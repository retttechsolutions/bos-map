"""Extract centroid points from ILS polygon features for lightweight initial map load."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from shapely.geometry import shape, mapping

log = logging.getLogger(__name__)


def build_points(features: list[dict], output_path: Path) -> None:
    """Create a GeoJSON FeatureCollection of ILS centroids.

    For features with no polygon geometry, the point is omitted.
    Properties are copied without the geometry.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    point_features: list[dict] = []
    for feat in features:
        raw_geom = feat.get("geometry")
        if not raw_geom:
            continue
        try:
            geom = shape(raw_geom)
            centroid = geom.centroid
            if centroid.is_empty:
                continue
            point_feat = {
                "type": "Feature",
                "properties": {
                    k: v for k, v in feat["properties"].items()
                    if k not in ("funkgruppen",)  # keep points lightweight
                },
                "geometry": {
                    "type": "Point",
                    "coordinates": [round(centroid.x, 6), round(centroid.y, 6)],
                },
            }
            point_features.append(point_feat)
        except Exception as exc:
            ils_id = feat.get("properties", {}).get("leitstellen_id", "?")
            log.warning("[%s] Could not compute centroid: %s", ils_id, exc)

    fc = {"type": "FeatureCollection", "features": point_features}
    output_path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    log.info("Points: wrote %d centroids → %s", len(point_features), output_path)
