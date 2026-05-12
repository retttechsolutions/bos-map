"""Build a serialized spatial index (flatbush-compatible) for client-side PiP queries.

The output JSON is loaded by the browser once and used with the rbush library
for O(log n) bounding-box pre-filtering before exact point-in-polygon tests.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

from shapely.geometry import shape

log = logging.getLogger(__name__)


def build_index(features: list[dict], output_path: Path) -> None:
    """Create a spatial index JSON file from ILS polygon features.

    Format: rbush-compatible array of {minX, minY, maxX, maxY, index}
    where 'index' is the position of the feature in the source features array.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    index_entries: list[dict] = []
    for i, feat in enumerate(features):
        raw_geom = feat.get("geometry")
        if not raw_geom:
            continue
        try:
            geom = shape(raw_geom)
            if geom.is_empty:
                continue
            minx, miny, maxx, maxy = geom.bounds
            index_entries.append({
                "minX": round(minx, 6),
                "minY": round(miny, 6),
                "maxX": round(maxx, 6),
                "maxY": round(maxy, 6),
                "index": i,
            })
        except Exception as exc:
            ils_id = feat.get("properties", {}).get("leitstellen_id", "?")
            log.warning("[%s] Could not index geometry: %s", ils_id, exc)

    # Wrap in an object so we can add metadata
    output = {
        "type": "ILSSpatialIndex",
        "version": 1,
        "count": len(index_entries),
        "entries": index_entries,
    }
    output_path.write_text(json.dumps(output, ensure_ascii=False), encoding="utf-8")
    log.info("Spatial index: %d entries → %s", len(index_entries), output_path)
