"""Generate static JSON files that form the BOS-Map "API".

Output structure under docs/api/v1/:
  index.json          - lightweight list of all ILS (no geometries)
  {leitstellen_id}.json - full GeoJSON Feature per ILS
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def build_api(features: list[dict], api_dir: Path) -> None:
    """Write all static API files to *api_dir*."""
    api_dir = Path(api_dir)
    api_dir.mkdir(parents=True, exist_ok=True)

    index_entries: list[dict] = []

    for feat in features:
        props = feat.get("properties") or {}
        ils_id: str = props.get("leitstellen_id", "")
        if not ils_id:
            continue

        # Full feature file
        out_file = api_dir / f"{ils_id}.json"
        out_file.write_text(json.dumps(feat, ensure_ascii=False, indent=2), encoding="utf-8")

        # Compute bbox for the index
        bbox: list[float] | None = None
        if feat.get("geometry"):
            try:
                from shapely.geometry import shape
                geom = shape(feat["geometry"])
                if not geom.is_empty:
                    minx, miny, maxx, maxy = geom.bounds
                    bbox = [round(minx, 4), round(miny, 4), round(maxx, 4), round(maxy, 4)]
            except Exception:
                pass

        index_entries.append({
            "leitstellen_id": ils_id,
            "leitstellenname": props.get("leitstellenname"),
            "bundesland": props.get("bundesland"),
            "traeger": props.get("traeger"),
            "adresse": props.get("adresse"),
            "review_status": props.get("review_status"),
            "bbox": bbox,
        })

    # Write index
    index_path = api_dir / "index.json"
    index_path.write_text(json.dumps(index_entries, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Static API: wrote %d feature files + index → %s", len(features), api_dir)


def build_metadata(
    features: list[dict],
    output_path: Path,
    pipeline_version: str = "0.1.0",
) -> None:
    """Write build metadata to metadata.json."""
    from datetime import datetime, timezone
    from collections import Counter

    bl_counts = Counter(
        f["properties"]["bundesland"] for f in features
        if f.get("properties", {}).get("bundesland")
    )
    review_counts = Counter(
        f["properties"].get("review_status", "unknown") for f in features
        if f.get("properties")
    )
    has_geometry = sum(1 for f in features if f.get("geometry"))

    metadata = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "pipeline_version": pipeline_version,
        "total_ils": len(features),
        "with_geometry": has_geometry,
        "by_bundesland": dict(sorted(bl_counts.items())),
        "by_review_status": dict(review_counts),
    }
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Metadata written → %s", output_path)
