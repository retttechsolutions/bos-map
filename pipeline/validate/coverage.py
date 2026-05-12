"""Check that harvested ILS features provide adequate coverage of Germany."""

from __future__ import annotations

import logging
from pathlib import Path

log = logging.getLogger(__name__)

# Expected minimum count per Bundesland (approximate, based on Wikipedia list)
_MIN_COUNTS: dict[str, int] = {
    "BW": 30, "BY": 24, "BE": 1, "BB": 5, "HB": 1,
    "HE": 10, "HH": 1, "MV": 5, "NI": 18, "NW": 52,
    "RP": 7, "SH": 6, "SL": 2, "SN": 8, "ST": 7, "TH": 8,
}

_GERMANY_MIN_COVERAGE = 0.90  # 90 % of Germany land area should be covered


def check_counts(features: list[dict]) -> dict[str, str]:
    """Warn if any Bundesland has fewer features than expected."""
    from collections import Counter
    warnings: dict[str, str] = {}
    counts = Counter(
        f["properties"]["bundesland"]
        for f in features
        if f.get("properties", {}).get("bundesland")
    )
    for bl, minimum in _MIN_COUNTS.items():
        actual = counts.get(bl, 0)
        if actual < minimum:
            msg = f"Expected >= {minimum} ILS for {bl}, found {actual}"
            warnings[bl] = msg
            log.warning(msg)
    return warnings


def check_coverage(features: list[dict], vg250_dir: Path | None = None) -> float | None:
    """Compute the fraction of Germany's land area covered by ILS polygons.

    Returns the coverage fraction (0.0–1.0) or None if VG250 is unavailable.
    """
    if vg250_dir is None:
        log.info("VG250 not available, skipping area coverage check")
        return None

    try:
        from harvest.bkg_vg250 import load_laender
        import shapely

        laender_gdf = load_laender(vg250_dir)
        germany = laender_gdf.geometry.union_all()
        germany_area = germany.area

        from shapely.geometry import shape
        ils_geoms = []
        for feat in features:
            if feat.get("geometry"):
                try:
                    ils_geoms.append(shape(feat["geometry"]))
                except Exception:
                    pass

        if not ils_geoms:
            return 0.0

        ils_union = shapely.unary_union(ils_geoms)
        intersection = ils_union.intersection(germany)
        coverage = intersection.area / germany_area if germany_area > 0 else 0.0

        log.info("Germany coverage: %.1f%%", coverage * 100)
        if coverage < _GERMANY_MIN_COVERAGE:
            log.warning(
                "Coverage %.1f%% is below minimum %.1f%%",
                coverage * 100,
                _GERMANY_MIN_COVERAGE * 100,
            )
        return coverage
    except Exception as exc:
        log.warning("Coverage check failed: %s", exc)
        return None
