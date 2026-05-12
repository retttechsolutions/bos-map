"""Geometry processing: validation, topology fixing, normalization to MultiPolygon."""

from __future__ import annotations

import json
import logging

import shapely
import shapely.validation
from shapely.geometry import MultiPolygon, Polygon, mapping, shape
from shapely.geometry.base import BaseGeometry

log = logging.getLogger(__name__)

# Tolerance for Douglas-Peucker simplification (degrees, ~11 m at German latitudes)
_SIMPLIFY_TOLERANCE = 0.0001


def process(geometry: BaseGeometry | dict | None, leitstellen_id: str = "?") -> dict | None:
    """Full geometry pipeline: fix → ensure MultiPolygon → simplify → validate.

    Accepts a Shapely geometry or a GeoJSON geometry dict.
    Returns a GeoJSON geometry dict (MultiPolygon) or None.
    """
    if geometry is None:
        return None

    geom = shape(geometry) if isinstance(geometry, dict) else geometry

    if geom.is_empty:
        log.warning("[%s] Empty geometry, skipping", leitstellen_id)
        return None

    geom = _fix(geom, leitstellen_id)
    geom = _to_multipolygon(geom, leitstellen_id)
    geom = _simplify(geom)

    if not geom.is_valid:
        log.error("[%s] Geometry still invalid after fix attempt", leitstellen_id)
        return None

    return json.loads(shapely.to_geojson(geom))


def _fix(geom: BaseGeometry, leitstellen_id: str) -> BaseGeometry:
    if geom.is_valid:
        return geom
    reason = shapely.validation.explain_validity(geom)
    log.warning("[%s] Invalid geometry (%s), applying make_valid", leitstellen_id, reason)
    fixed = shapely.make_valid(geom)
    return fixed


def _to_multipolygon(geom: BaseGeometry, leitstellen_id: str) -> MultiPolygon:
    """Normalize any geometry to MultiPolygon."""
    if isinstance(geom, MultiPolygon):
        return geom
    if isinstance(geom, Polygon):
        return MultiPolygon([geom])
    # make_valid can return GeometryCollection; extract polygon parts
    if hasattr(geom, "geoms"):
        polys = [g for g in geom.geoms if isinstance(g, (Polygon, MultiPolygon))]
        if not polys:
            log.warning("[%s] No polygon parts found in geometry collection", leitstellen_id)
            return MultiPolygon()
        parts: list[Polygon] = []
        for p in polys:
            if isinstance(p, MultiPolygon):
                parts.extend(p.geoms)
            else:
                parts.append(p)
        return MultiPolygon(parts)
    log.warning("[%s] Unexpected geometry type %s", leitstellen_id, geom.geom_type)
    return MultiPolygon()


def _simplify(geom: MultiPolygon) -> MultiPolygon:
    simplified = geom.simplify(_SIMPLIFY_TOLERANCE, preserve_topology=True)
    if isinstance(simplified, MultiPolygon):
        return simplified
    return _to_multipolygon(simplified, "simplify")


def shapely_from_geojson(geojson_geometry: dict) -> BaseGeometry:
    return shape(geojson_geometry)
