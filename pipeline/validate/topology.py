"""Geometry topology validation for ILS features."""

from __future__ import annotations

import logging
from typing import Any

import shapely
from shapely.geometry import shape

log = logging.getLogger(__name__)

# Germany bounding box (loose)
_DE_BOUNDS = (5.5, 47.0, 15.5, 55.5)


def validate_geometry(feature: dict) -> list[str]:
    """Return topology error messages for a single feature's geometry."""
    errors: list[str] = []
    ils_id = feature.get("properties", {}).get("leitstellen_id", "?")
    raw_geom = feature.get("geometry")

    if raw_geom is None:
        return []  # null geometry is allowed (not all features have polygons yet)

    try:
        geom = shape(raw_geom)
    except Exception as exc:
        return [f"Cannot parse geometry: {exc}"]

    if geom.is_empty:
        errors.append("Empty geometry")
        return errors

    if not geom.is_valid:
        reason = shapely.validation.explain_validity(geom)
        errors.append(f"Invalid geometry: {reason}")

    if geom.geom_type != "MultiPolygon":
        errors.append(f"Expected MultiPolygon, got {geom.geom_type}")

    bounds = geom.bounds  # (minx, miny, maxx, maxy)
    if not _in_germany(bounds):
        errors.append(f"Geometry bbox outside Germany: {bounds}")

    return errors


def _in_germany(bounds: tuple) -> bool:
    minx, miny, maxx, maxy = bounds
    dminx, dminy, dmaxx, dmaxy = _DE_BOUNDS
    return (
        minx >= dminx - 1 and miny >= dminy - 1
        and maxx <= dmaxx + 1 and maxy <= dmaxy + 1
    )


def validate_all(features: list[dict]) -> dict[str, list[str]]:
    """Run topology checks on all features. Returns id → errors mapping."""
    all_errors: dict[str, list[str]] = {}
    for feat in features:
        ils_id = feat.get("properties", {}).get("leitstellen_id", "?")
        errors = validate_geometry(feat)
        if errors:
            all_errors[ils_id] = errors
            for err in errors:
                log.warning("[%s] %s", ils_id, err)
    return all_errors
