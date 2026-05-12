"""CRS normalization: reproject any geometry to EPSG:4326 (WGS84)."""

from __future__ import annotations

import logging
from functools import lru_cache

import pyproj
import shapely.ops
from shapely.geometry.base import BaseGeometry

log = logging.getLogger(__name__)

# Bounding box for Germany (very loose, catches grossly wrong reprojections)
_DE_BOUNDS = (5.5, 47.0, 15.5, 55.5)  # min_lon, min_lat, max_lon, max_lat

WGS84 = "EPSG:4326"


@lru_cache(maxsize=32)
def _transformer(source_crs: str) -> pyproj.Transformer:
    return pyproj.Transformer.from_crs(source_crs, WGS84, always_xy=True)


def reproject(geometry: BaseGeometry, source_crs: str) -> BaseGeometry:
    """Reproject *geometry* from *source_crs* to WGS84.

    Returns the reprojected geometry.  Raises ValueError if the result falls
    outside the expected Germany bounding box.
    """
    if source_crs.upper() in (WGS84, "EPSG:4326", "CRS84", "OGC:CRS84"):
        return geometry

    transformer = _transformer(source_crs.upper())
    reprojected = shapely.ops.transform(transformer.transform, geometry)

    bounds = reprojected.bounds  # (minx, miny, maxx, maxy)
    if not _within_germany(bounds):
        raise ValueError(
            f"Reprojected geometry from {source_crs} falls outside Germany: {bounds}"
        )
    return reprojected


def _within_germany(bounds: tuple[float, float, float, float]) -> bool:
    min_lon, min_lat, max_lon, max_lat = bounds
    de_min_lon, de_min_lat, de_max_lon, de_max_lat = _DE_BOUNDS
    return (
        min_lon >= de_min_lon - 1
        and min_lat >= de_min_lat - 1
        and max_lon <= de_max_lon + 1
        and max_lat <= de_max_lat + 1
    )


def detect_crs_from_wfs_capabilities(xml_text: str) -> str | None:
    """Parse a WFS GetCapabilities response and return the default CRS string."""
    import re

    # Look for DefaultCRS or DefaultSRS tags
    match = re.search(
        r"<(?:ows:)?(?:Default(?:CRS|SRS))>([^<]+)</",
        xml_text,
    )
    if match:
        return match.group(1).strip()
    # Fallback: first SupportedCRS
    match = re.search(r"<(?:ows:)?(?:Supported(?:CRS|SRS))>([^<]+)</", xml_text)
    if match:
        return match.group(1).strip()
    return None
