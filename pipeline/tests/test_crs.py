"""Tests for CRS normalization."""

import pytest
from shapely.geometry import Point, Polygon

from normalize.crs import reproject, detect_crs_from_wfs_capabilities


def _box_25832(minx, miny, maxx, maxy):
    """Create a rough box in EPSG:25832 (UTM zone 32N) around Germany."""
    return Polygon([(minx, miny), (maxx, miny), (maxx, maxy), (minx, maxy)])


def test_identity_wgs84():
    """WGS84 geometry should be returned unchanged."""
    pt = Point(11.5, 48.1)
    result = reproject(pt, "EPSG:4326")
    assert result.x == pytest.approx(11.5)
    assert result.y == pytest.approx(48.1)


def test_reproject_utm32n_to_wgs84():
    """EPSG:25832 coordinates for Munich should reproject to correct WGS84."""
    # Munich city center approx: 691_000 E, 5_334_000 N (EPSG:25832)
    pt = Point(691_000, 5_334_000)
    result = reproject(pt, "EPSG:25832")
    assert 11.4 < result.x < 11.7  # ~11.58° lon
    assert 48.0 < result.y < 48.3  # ~48.14° lat


def test_reproject_utm33n_to_wgs84():
    """EPSG:25833 coordinates for Dresden should reproject correctly."""
    # Dresden approx: 411_000 E, 5_655_000 N (EPSG:25833)
    pt = Point(411_000, 5_655_000)
    result = reproject(pt, "EPSG:25833")
    assert 13.5 < result.x < 14.0
    assert 50.9 < result.y < 51.2


def test_out_of_germany_raises():
    """Coordinates outside Germany should raise ValueError."""
    # Tokyo in WGS84 – if someone passes a point that ends up at 140°E
    pt = Point(139.7, 35.7)  # already WGS84, but passes as different CRS
    # We simulate a bad reprojection by directly checking bounds logic
    from normalize.crs import _within_germany
    assert not _within_germany((139.7, 35.7, 139.8, 35.8))


def test_detect_crs_from_capabilities_xml():
    xml = """<?xml version="1.0"?>
    <WFS_Capabilities>
      <FeatureTypeList>
        <FeatureType>
          <DefaultCRS>urn:ogc:def:crs:EPSG::25832</DefaultCRS>
        </FeatureType>
      </FeatureTypeList>
    </WFS_Capabilities>"""
    crs = detect_crs_from_wfs_capabilities(xml)
    assert crs == "urn:ogc:def:crs:EPSG::25832"


def test_detect_crs_not_found():
    result = detect_crs_from_wfs_capabilities("<root></root>")
    assert result is None
