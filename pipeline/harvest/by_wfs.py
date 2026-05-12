"""Harvest Bayern ILS data from the Verwaltungsatlas StMI WFS.

Source: Bayerische Staatsregierung
Licence: CC BY-SA 4.0
URL: https://gdiserv.bayern.de/srv1970/services/verwaltungsatlas_stmi-wfs
Layers:
  - IntegrierteLeitstellenFlaeche  (polygon areas)
  - IntegrierteLeitstellenStandort (point locations)
"""

from __future__ import annotations

import io
import json
import logging
import time
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

_WFS_BASE = "https://gdiserv.bayern.de/srv1970/services/verwaltungsatlas_stmi-wfs"
_LAYER_FLAECHE = "IntegrierteLeitstellenFlaeche"
_LAYER_STANDORT = "IntegrierteLeitstellenStandort"
_MAX_RETRIES = 4


def _fetch_layer_gdf(layer: str):
    """Fetch a WFS layer via OWSLib + GML and return as GeoDataFrame in WGS84."""
    import geopandas as gpd
    from owslib.wfs import WebFeatureService

    delay = 2.0
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            wfs = WebFeatureService(url=_WFS_BASE, version="2.0.0", timeout=120)
            response = wfs.getfeature(typename=[layer], maxfeatures=2000)
            raw_bytes = response.read()
            gdf = gpd.read_file(io.BytesIO(raw_bytes))
            if gdf.crs and gdf.crs.to_epsg() != 4326:
                gdf = gdf.to_crs(epsg=4326)
            return gdf
        except Exception as exc:
            last_exc = exc
            log.warning(
                "Attempt %d/%d failed for layer %s: %s – retrying in %.0fs",
                attempt, _MAX_RETRIES, layer, exc, delay,
            )
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"WFS fetch failed for {layer} after {_MAX_RETRIES} attempts") from last_exc


def harvest(output_dir: Path, force: bool = False) -> dict[str, Path]:
    """Fetch Bayern ILS layers and write raw GeoJSON files to *output_dir*.

    Returns a dict with keys 'flaeche' and 'standort' pointing to output files.
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths: dict[str, Path] = {
        "flaeche": output_dir / "by_ils_flaeche.geojson",
        "standort": output_dir / "by_ils_standort.geojson",
    }

    for key, layer, path in [
        ("flaeche", _LAYER_FLAECHE, paths["flaeche"]),
        ("standort", _LAYER_STANDORT, paths["standort"]),
    ]:
        if path.exists() and not force:
            log.info("Bayern %s already harvested at %s", layer, path)
            continue
        log.info("Fetching Bayern WFS layer %s…", layer)
        gdf = _fetch_layer_gdf(layer)
        # Timestamp columns are not JSON-serializable; convert to ISO strings
        for col in gdf.select_dtypes(include=["datetime64[ns]", "datetimetz"]).columns:
            gdf[col] = gdf[col].astype(str)
        path.write_text(gdf.to_json(), encoding="utf-8")
        log.info("Saved %d features → %s", len(gdf), path)

    return paths


def load(output_dir: Path) -> tuple[list[dict], list[dict]]:
    """Return (flaeche_features, standort_features) loaded from disk."""
    output_dir = Path(output_dir)
    flaeche = json.loads((output_dir / "by_ils_flaeche.geojson").read_text("utf-8"))["features"]
    standort = json.loads((output_dir / "by_ils_standort.geojson").read_text("utf-8"))["features"]
    return flaeche, standort


def normalize(output_dir: Path) -> list[dict[str, Any]]:
    """Read raw Bayern features and return canonical ILS feature dicts."""
    from normalize import geometry as geom_mod
    from normalize import schema as schema_mod
    from shapely.geometry import shape

    flaeche_features, standort_features = load(output_dir)

    # Build lookup from standort layer: name → properties
    standort_by_name: dict[str, dict] = {}
    for feat in standort_features:
        props = feat.get("properties") or {}
        name = props.get("NAME") or props.get("name") or ""
        standort_by_name[name.strip()] = props

    results: list[dict] = []
    for feat in flaeche_features:
        props = feat.get("properties") or {}
        raw_name: str = (props.get("NAME") or props.get("name") or "").strip()
        if not raw_name:
            log.warning("Bayern feature missing NAME, skipping")
            continue

        short = _make_short(raw_name)
        ils_id = schema_mod.build_id("BY", short)

        raw_geom = feat.get("geometry")
        geom_shapely = shape(raw_geom) if raw_geom else None
        processed_geom = geom_mod.process(geom_shapely, ils_id) if geom_shapely else None

        st_props = standort_by_name.get(raw_name, {})
        adresse = st_props.get("ADRESSE") or props.get("ADRESSE")
        telefon = st_props.get("TELEFON") or props.get("TELEFON")

        result = schema_mod.canonical_feature(
            leitstellen_id=ils_id,
            leitstellenname=f"ILS {raw_name}",
            bundesland="BY",
            geometry=processed_geom,
            quelltyp="amtlich_wfs",
            geometry_basis="amtliche_grenze",
            source_url=_WFS_BASE,
            source_crs="EPSG:4326",
            adresse=adresse,
            telefon=telefon,
            review_status="verified",
        )
        results.append(result)

    log.info("Bayern: normalized %d ILS", len(results))
    return results


def _make_short(name: str) -> str:
    replacements = {
        "Ä": "AE", "Ö": "OE", "Ü": "UE", "ä": "ae", "ö": "oe", "ü": "ue", "ß": "SS",
    }
    result = name
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = "".join(c for c in result if c.isalnum())
    return result[:6].upper()


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    parser = argparse.ArgumentParser(description="Harvest Bayern WFS ILS data")
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    harvest(Path(args.output), force=args.force)
