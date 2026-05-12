"""Harvest Sachsen ILS / Rettungsdienst data from the Verwaltungsatlas Sachsen.

Source: Sächsisches Staatsministerium für Infrastruktur und Landesentwicklung
Licence: dl-de/by-2-0
WMS: https://geodienste.sachsen.de/wms_smr_gesundheit/guest
Layers:
  - Zustaendigkeitsbereiche der Rettungsdiensttraeger (polygons)
  - Standorte der Rettungsleitstellen (points)

Note: WMS does not expose raw vector data. We use the OGC WFS endpoint if available,
otherwise fall back to requesting the FileGDB download from the open data portal.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

# WMS for reference / visualization
_WMS_BASE = "https://geodienste.sachsen.de/wms_smr_gesundheit/guest"

# Open data download URL for the Verwaltungsatlas Rettungsdienst
# Sachsen open data portal (GDI Sachsen), dl-de/by-2-0
_OPENDATA_URL = (
    "https://www.geodaten.sachsen.de/downloadbereich-digitale-verwaltungsgrenzen-4172.html"
)

# WFS endpoint (may not be publicly available; attempt it first)
_WFS_BASE = "https://geodienste.sachsen.de/wfs_smr_gesundheit/guest"
_LAYER_BEREICHE = "smr_gesundheit:Zustaendigkeitsbereiche_Rettungsdiensttraeger"
_LAYER_LEITSTELLEN = "smr_gesundheit:Standorte_Rettungsleitstellen"
_CRS = "EPSG:25833"
_MAX_RETRIES = 4


def _wfs_params(type_name: str) -> dict:
    return {
        "service": "WFS",
        "request": "GetFeature",
        "version": "2.0.0",
        "typeNames": type_name,
        "srsName": _CRS,
        "outputFormat": "application/json",
        "count": "500",
    }


def _fetch_wfs(url: str, params: dict) -> dict | None:
    delay = 2.0
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=60, follow_redirects=True) as client:
                resp = client.get(url, params=params)
                if resp.status_code == 404:
                    return None
                resp.raise_for_status()
                return resp.json()
        except httpx.HTTPStatusError:
            return None
        except Exception as exc:
            log.warning("SN WFS attempt %d failed: %s", attempt, exc)
            time.sleep(delay)
            delay *= 2
    return None


def harvest(output_dir: Path, force: bool = False) -> dict[str, Path]:
    """Attempt WFS harvest; write raw GeoJSON files to *output_dir*."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = {
        "bereiche": output_dir / "sn_rettungsdienst_bereiche.geojson",
        "leitstellen": output_dir / "sn_rettungsleitstellen.geojson",
    }

    for key, layer, path in [
        ("bereiche", _LAYER_BEREICHE, paths["bereiche"]),
        ("leitstellen", _LAYER_LEITSTELLEN, paths["leitstellen"]),
    ]:
        if path.exists() and not force:
            log.info("Sachsen %s already harvested", key)
            continue

        log.info("Attempting WFS fetch for Sachsen layer %s…", layer)
        data = _fetch_wfs(_WFS_BASE, _wfs_params(layer))

        if data is None:
            log.warning(
                "WFS not available for Sachsen layer %s. "
                "Manual download required from: %s",
                layer,
                _OPENDATA_URL,
            )
            # Write a placeholder so the pipeline can continue
            placeholder = {
                "type": "FeatureCollection",
                "features": [],
                "_placeholder": True,
                "_manual_download_url": _OPENDATA_URL,
            }
            path.write_text(json.dumps(placeholder, ensure_ascii=False, indent=2), encoding="utf-8")
            continue

        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("SN %s: saved %d features → %s", key, len(data.get("features", [])), path)

    return paths


def normalize(output_dir: Path) -> list[dict[str, Any]]:
    """Read raw Sachsen features and return canonical ILS feature dicts."""
    from normalize import crs as crs_mod
    from normalize import geometry as geom_mod
    from normalize import schema as schema_mod
    from shapely.geometry import shape

    output_dir = Path(output_dir)
    bereiche_path = output_dir / "sn_rettungsdienst_bereiche.geojson"
    leitstellen_path = output_dir / "sn_rettungsleitstellen.geojson"

    if not bereiche_path.exists():
        log.warning("Sachsen raw data not found, skipping normalize")
        return []

    bereiche_raw = json.loads(bereiche_path.read_text("utf-8"))
    if bereiche_raw.get("_placeholder"):
        log.warning("Sachsen data is placeholder (manual download required), skipping")
        return []

    leitstellen_raw = {}
    if leitstellen_path.exists():
        leitstellen_raw_data = json.loads(leitstellen_path.read_text("utf-8"))
        # Build lookup by name
        for feat in leitstellen_raw_data.get("features", []):
            props = feat.get("properties") or {}
            name = props.get("NAME") or props.get("name") or ""
            leitstellen_raw[name.strip()] = props

    results: list[dict] = []
    for feat in bereiche_raw.get("features", []):
        props = feat.get("properties") or {}
        name: str = (props.get("NAME") or props.get("TRAEGER") or "").strip()
        if not name:
            continue

        short = _sn_short(name)
        ils_id = schema_mod.build_id("SN", short)

        raw_geom = feat.get("geometry")
        processed_geom = None
        if raw_geom:
            try:
                geom_shape = shape(raw_geom)
                reprojected = crs_mod.reproject(geom_shape, _CRS)
                processed_geom = geom_mod.process(reprojected, ils_id)
            except Exception as exc:
                log.warning("[%s] Geometry processing failed: %s", ils_id, exc)

        traeger = props.get("TRAEGER") or name
        st_props = leitstellen_raw.get(name, {})
        adresse = st_props.get("ADRESSE") or props.get("ADRESSE")

        result = schema_mod.canonical_feature(
            leitstellen_id=ils_id,
            leitstellenname=name,
            bundesland="SN",
            geometry=processed_geom,
            quelltyp="amtlich_wfs",
            geometry_basis="amtliche_grenze",
            source_url=_WFS_BASE,
            source_crs=_CRS,
            traeger=traeger,
            adresse=adresse,
            review_status="verified" if processed_geom else "needs_review",
        )
        results.append(result)

    log.info("Sachsen: normalized %d ILS", len(results))
    return results


def _sn_short(name: str) -> str:
    replacements = {"Ä": "AE", "Ö": "OE", "Ü": "UE", "ä": "ae", "ö": "oe", "ü": "ue", "ß": "SS"}
    result = name
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = "".join(c for c in result if c.isalnum())
    return result[:6].upper()


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    parser = argparse.ArgumentParser(description="Harvest Sachsen WMS/WFS ILS data")
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    harvest(Path(args.output), force=args.force)
