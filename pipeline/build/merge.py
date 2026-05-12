"""Merge normalized per-state ILS feature files into a single GeoJSON FeatureCollection."""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def merge(input_dir: Path, output_path: Path) -> list[dict]:
    """Read all *.geojson files in *input_dir* and write a merged FeatureCollection.

    Deduplicates by leitstellen_id: official sources (amtlich_wfs, amtlich_ogcapi)
    take priority over community/derived sources.
    """
    input_dir = Path(input_dir)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    # Priority ordering: lower = higher priority
    _priority = {
        "amtlich_wfs": 0,
        "amtlich_ogcapi": 0,
        "amtlich_html": 1,
        "recht_abgeleitet": 2,
        "community": 3,
    }

    features_by_id: dict[str, dict] = {}

    for geojson_file in sorted(input_dir.glob("*.geojson")):
        data = json.loads(geojson_file.read_text("utf-8"))
        source_features = data.get("features", [])
        log.info("Loading %d features from %s", len(source_features), geojson_file.name)

        for feat in source_features:
            ils_id = feat.get("properties", {}).get("leitstellen_id")
            if not ils_id:
                continue

            if ils_id not in features_by_id:
                features_by_id[ils_id] = feat
            else:
                existing_quelltyp = features_by_id[ils_id]["properties"].get("quelltyp", "community")
                new_quelltyp = feat["properties"].get("quelltyp", "community")
                if _priority.get(new_quelltyp, 99) < _priority.get(existing_quelltyp, 99):
                    log.debug("Replacing %s with higher-priority source (%s → %s)",
                              ils_id, existing_quelltyp, new_quelltyp)
                    features_by_id[ils_id] = feat

    merged = sorted(features_by_id.values(),
                    key=lambda f: f["properties"].get("leitstellen_id", ""))

    feature_collection = {"type": "FeatureCollection", "features": merged}
    output_path.write_text(json.dumps(feature_collection, ensure_ascii=False), encoding="utf-8")
    log.info("Merged %d unique ILS → %s", len(merged), output_path)
    return merged
