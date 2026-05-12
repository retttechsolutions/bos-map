"""Tests for geometry processing."""

import json

import pytest
from shapely.geometry import MultiPolygon, Point, Polygon, mapping

from normalize.geometry import process, _to_multipolygon


def _make_polygon(coords=None):
    if coords is None:
        # Simple square near Munich
        coords = [(11.5, 48.0), (11.6, 48.0), (11.6, 48.1), (11.5, 48.1), (11.5, 48.0)]
    return Polygon(coords)


def test_process_returns_multipolygon_dict():
    poly = _make_polygon()
    result = process(poly, "TEST-001")
    assert result is not None
    assert result["type"] == "MultiPolygon"


def test_process_from_geojson_dict():
    poly = _make_polygon()
    geojson_geom = json.loads(mapping(poly).__class__(mapping(poly)).__repr__()
                               .replace("'", '"'))
    # Use json.loads(json.dumps(mapping(poly)))
    geojson_geom = json.loads(json.dumps(dict(mapping(poly))))
    result = process(geojson_geom, "TEST-002")
    assert result is not None
    assert result["type"] == "MultiPolygon"


def test_process_none_geometry():
    result = process(None, "TEST-003")
    assert result is None


def test_process_invalid_geometry_auto_fixed():
    # Self-intersecting bowtie polygon (invalid)
    bowtie = Polygon([(0, 0), (1, 1), (1, 0), (0, 1), (0, 0)])
    assert not bowtie.is_valid
    result = process(bowtie, "TEST-004")
    # Should be fixed and returned as MultiPolygon dict
    assert result is not None


def test_to_multipolygon_from_polygon():
    poly = _make_polygon()
    result = _to_multipolygon(poly, "X")
    assert isinstance(result, MultiPolygon)


def test_to_multipolygon_from_multipolygon():
    mp = MultiPolygon([_make_polygon()])
    result = _to_multipolygon(mp, "X")
    assert isinstance(result, MultiPolygon)
    assert result is mp


def test_process_outside_germany_still_returns():
    # A polygon well outside Germany – process() only validates CRS, not bounds
    poly = Polygon([(30.0, 50.0), (31.0, 50.0), (31.0, 51.0), (30.0, 51.0)])
    result = process(poly, "TEST-005")
    # process() does not do bounds checking; that's the topology validator's job
    assert result is not None
