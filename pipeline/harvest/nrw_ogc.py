"""Harvest NRW Feuerwehrleitstellen via OGC API Features.

Source: Ministerium des Innern NRW / IT.NRW
Licence: dl-de/by-2-0
URL: https://ogc-api.nrw.de/inspire-us-feuerwehr/v1/
Note: Point data only – polygons are derived from VG250 Landkreise.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

import httpx

log = logging.getLogger(__name__)

_BASE_URL = "https://ogc-api.nrw.de/inspire-us-feuerwehr/v1"
_COLLECTION = "governmentalservice"  # confirmed from OGC API collections
_MAX_RETRIES = 4
_PAGE_SIZE = 100


def _get_json(url: str, params: dict | None = None) -> dict:
    delay = 2.0
    last_exc: Exception | None = None
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=30, follow_redirects=True) as client:
                resp = client.get(url, params=params or {})
                resp.raise_for_status()
                return resp.json()
        except Exception as exc:
            last_exc = exc
            log.warning("Attempt %d/%d failed: %s", attempt, _MAX_RETRIES, exc)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError(f"OGC API fetch failed: {url}") from last_exc


def _discover_collection(base_url: str) -> str:
    """Try to find the correct collection name for fire/rescue dispatch centers."""
    data = _get_json(f"{base_url}/collections", {"f": "json"})
    collections = data.get("collections", [])
    for col in collections:
        col_id = col.get("id", "")
        title = col.get("title", "").lower()
        if "leitstelle" in col_id.lower() or "leitstelle" in title:
            log.info("Found collection: %s (%s)", col_id, title)
            return col_id
    # Fallback: return first available
    if collections:
        fallback = collections[0]["id"]
        log.warning("Could not identify Leitstellen collection, using: %s", fallback)
        return fallback
    raise RuntimeError("No collections found at OGC API")


def harvest(output_dir: Path, force: bool = False) -> Path:
    """Paginate through OGC API Features and write raw GeoJSON to *output_dir*."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "nrw_leitstellen.geojson"

    if out_path.exists() and not force:
        log.info("NRW data already harvested at %s", out_path)
        return out_path

    # Discover the right collection
    try:
        collection_id = _discover_collection(_BASE_URL)
    except Exception:
        log.warning("Collection discovery failed, using default: %s", _COLLECTION)
        collection_id = _COLLECTION

    items_url = f"{_BASE_URL}/collections/{collection_id}/items"
    all_features: list[dict] = []
    offset = 0

    while True:
        params = {
            "f": "json",
            "limit": str(_PAGE_SIZE),
            "offset": str(offset),
            "crs": "http://www.opengis.net/def/crs/OGC/1.3/CRS84",
        }
        log.info("Fetching NRW items offset=%d…", offset)
        page = _get_json(items_url, params)
        features = page.get("features", [])
        all_features.extend(features)

        # Check if there are more pages
        next_link = next(
            (lnk["href"] for lnk in page.get("links", []) if lnk.get("rel") == "next"),
            None,
        )
        if not next_link or len(features) < _PAGE_SIZE:
            break
        offset += _PAGE_SIZE

    feature_collection = {
        "type": "FeatureCollection",
        "features": all_features,
        "numberMatched": len(all_features),
    }
    out_path.write_text(json.dumps(feature_collection, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("NRW: saved %d features → %s", len(all_features), out_path)
    return out_path


def normalize(output_dir: Path, vg250_dir: Path | None = None) -> list[dict[str, Any]]:
    """Read raw NRW features, derive polygons from VG250, return canonical features."""
    from normalize import schema as schema_mod
    from normalize import geometry as geom_mod

    raw_path = Path(output_dir) / "nrw_leitstellen.geojson"
    if not raw_path.exists():
        raise FileNotFoundError(f"Run harvest first: {raw_path}")

    raw = json.loads(raw_path.read_text("utf-8"))
    features = raw.get("features", [])

    # Load VG250 Kreise for polygon derivation if available
    kreise_gdf = None
    if vg250_dir and Path(vg250_dir).exists():
        try:
            from harvest.bkg_vg250 import load_kreise
            kreise_gdf = load_kreise(vg250_dir)
        except Exception as exc:
            log.warning("Could not load VG250 Kreise: %s", exc)

    results: list[dict] = []
    for feat in features:
        props = feat.get("properties") or {}

        # NRW OGC API field names (from INSPIRE US Feuerwehr schema)
        name: str = (
            props.get("name")
            or props.get("localname")
            or props.get("Leitstelle")
            or ""
        ).strip()
        if not name:
            log.warning("NRW feature missing name, skipping")
            continue

        kreis = props.get("Kreis") or props.get("kreis") or ""
        adresse = props.get("Adresse") or props.get("adresse")
        telefon = props.get("Telefon") or props.get("telefon")

        short = _nrw_short(name)
        ils_id = schema_mod.build_id("NW", short)

        # Derive polygon from VG250 by matching Kreis name
        processed_geom = None
        geometry_basis = "community"
        if kreise_gdf is not None and kreis:
            try:
                processed_geom = _derive_polygon(kreise_gdf, kreis, ils_id)
                geometry_basis = "verwaltungsgrenze_abgeleitet"
            except Exception as exc:
                log.warning("[%s] Polygon derivation failed: %s", ils_id, exc)

        result = schema_mod.canonical_feature(
            leitstellen_id=ils_id,
            leitstellenname=name,
            bundesland="NW",
            geometry=processed_geom,
            quelltyp="amtlich_ogcapi",
            geometry_basis=geometry_basis,
            source_url=f"{_BASE_URL}/collections/",
            adresse=adresse,
            telefon=telefon,
            review_status="verified" if processed_geom else "needs_review",
        )
        results.append(result)

    log.info("NRW: normalized %d ILS", len(results))
    return results


def _derive_polygon(kreise_gdf, kreis_name: str, ils_id: str) -> dict | None:
    """Union VG250 Kreise matching *kreis_name* into a single MultiPolygon."""
    import json
    import shapely
    from normalize import geometry as geom_mod

    mask = kreise_gdf["GEN"].str.contains(kreis_name, case=False, na=False)
    matching = kreise_gdf[mask]
    if matching.empty:
        # Try partial match
        words = kreis_name.split()
        for word in words:
            if len(word) > 3:
                mask = kreise_gdf["GEN"].str.contains(word, case=False, na=False)
                matching = kreise_gdf[mask]
                if not matching.empty:
                    break
    if matching.empty:
        raise ValueError(f"No Kreis match for: {kreis_name!r}")

    union = matching.geometry.union_all()
    return geom_mod.process(union, ils_id)


def _nrw_short(name: str) -> str:
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
    parser = argparse.ArgumentParser(description="Harvest NRW OGC API ILS data")
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    harvest(Path(args.output), force=args.force)
