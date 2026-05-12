"""Derive ILS polygons from BKG VG250 administrative boundaries.

Used for states where no official polygon geodata service exists but the
legal assignment of Landkreise to Leitstellen is known (Brandenburg, BW, etc.).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

# ── Brandenburg ───────────────────────────────────────────────────────────────
# Source: Regionalleitstellenverordnung Brandenburg (RettZEntV BB)
# 5 Regionalleitstellen, each covers specific Landkreise / kreisfreie Städte.
# GEN field names from VG250_KRS.shp

_BB_ASSIGNMENTS: dict[str, list[str]] = {
    "Leitstelle Nord": [
        "Prignitz", "Ostprignitz-Ruppin", "Oberhavel", "Havelland",
        "Neuruppin",  # Kreisfreie Stadt (if any)
    ],
    "Leitstelle Ost": [
        "Barnim", "Märkisch-Oderland", "Oder-Spree",
        "Frankfurt (Oder)",
    ],
    "Leitstelle Süd": [
        "Dahme-Spreewald", "Teltow-Fläming", "Elbe-Elster", "Spree-Neiße",
        "Cottbus",
    ],
    "Leitstelle West": [
        "Potsdam-Mittelmark", "Brandenburg an der Havel",
        "Potsdam",
    ],
    "Leitstelle Lausitz": [
        "Oberspreewald-Lausitz",
    ],
}

# ── Baden-Württemberg ─────────────────────────────────────────────────────────
# 35 Rettungsdienstbereiche, mostly aligned with Landkreise.
# Abbreviated list (key Phase-2 ILS only, expand in Phase 3):
_BW_ASSIGNMENTS: dict[str, list[str]] = {
    "Leitstelle Karlsruhe": ["Karlsruhe", "Karlsruhe (Stadtkreis)"],
    "Leitstelle Stuttgart": ["Stuttgart"],
    "Leitstelle Freiburg": ["Freiburg im Breisgau"],
    "Leitstelle Ulm": ["Ulm", "Alb-Donau-Kreis"],
    "Leitstelle Heilbronn": ["Heilbronn", "Heilbronn (Stadtkreis)"],
    "Leitstelle Mannheim": ["Mannheim"],
    "Leitstelle Heidelberg": ["Heidelberg", "Rhein-Neckar-Kreis"],
    "Leitstelle Reutlingen": ["Reutlingen", "Tübingen"],
    "Leitstelle Konstanz": ["Konstanz"],
    "Leitstelle Ravensburg": ["Ravensburg", "Bodenseekreis"],
    "Leitstelle Pforzheim": ["Pforzheim", "Enzkreis", "Calw"],
    "Leitstelle Offenburg": ["Ortenaukreis"],
    "Leitstelle Rottweil": ["Rottweil", "Tuttlingen"],
    "Leitstelle Göppingen": ["Göppingen"],
    "Leitstelle Esslingen": ["Esslingen"],
    "Leitstelle Ludwigsburg": ["Ludwigsburg"],
    "Leitstelle Waiblingen": ["Rems-Murr-Kreis"],
    "Leitstelle Aalen": ["Ostalbkreis"],
    "Leitstelle Schwäbisch Hall": ["Schwäbisch Hall"],
    "Leitstelle Heidenheim": ["Heidenheim"],
    "Leitstelle Sigmaringen": ["Sigmaringen"],
    "Leitstelle Biberach": ["Biberach"],
    "Leitstelle Waldshut": ["Waldshut"],
    "Leitstelle Lörrach": ["Lörrach"],
    "Leitstelle Breisgau-Hochschwarzwald": ["Breisgau-Hochschwarzwald"],
    "Leitstelle Emmendingen": ["Emmendingen"],
    "Leitstelle Schwarzwald-Baar": ["Schwarzwald-Baar-Kreis"],
    "Leitstelle Freudenstadt": ["Freudenstadt"],
    "Leitstelle Zollernalbkreis": ["Zollernalbkreis"],
    "Leitstelle Main-Tauber": ["Main-Tauber-Kreis"],
    "Leitstelle Hohenlohe": ["Hohenlohekreis"],
    "Leitstelle Neckar-Odenwald": ["Neckar-Odenwald-Kreis"],
    "Leitstelle Rhein-Neckar": ["Rhein-Neckar-Kreis"],
    "Leitstelle Rastatt": ["Rastatt", "Baden-Baden"],
    "Leitstelle Böblingen": ["Böblingen"],
}


def derive(
    bl_code: str,
    kreise_gdf,
    assignments: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Build canonical feature stubs for a Bundesland using Kreis assignments.

    Args:
        bl_code: two-letter Bundesland code (e.g. "BB")
        kreise_gdf: GeoDataFrame of VG250_KRS in EPSG:4326
        assignments: mapping of Leitstellen name → list of Kreis GEN values

    Returns:
        List of canonical GeoJSON Feature dicts.
    """
    from normalize import geometry as geom_mod
    from normalize import schema as schema_mod

    results: list[dict] = []

    for ils_name, kreis_names in assignments.items():
        ils_id = schema_mod.build_id(bl_code, _short(ils_name))

        # Match Kreise
        matched = _match_kreise(kreise_gdf, kreis_names, ils_id)
        if matched.empty:
            log.warning("[%s] No Kreise found for: %s", ils_id, kreis_names)
            processed_geom = None
            geometry_basis = "community"
            review_status = "needs_review"
        else:
            union = matched.geometry.union_all()
            processed_geom = geom_mod.process(union, ils_id)
            geometry_basis = "verwaltungsgrenze_abgeleitet"
            review_status = "needs_review"

        result = schema_mod.canonical_feature(
            leitstellen_id=ils_id,
            leitstellenname=ils_name,
            bundesland=bl_code,
            geometry=processed_geom,
            quelltyp="recht_abgeleitet",
            geometry_basis=geometry_basis,
            source_url=None,
            review_status=review_status,
            bemerkung=f"Polygon aus VG250-Kreisen abgeleitet: {', '.join(kreis_names)}",
        )
        results.append(result)

    return results


def _match_kreise(kreise_gdf, kreis_names: list[str], ils_id: str):
    """Return subset of kreise_gdf matching any name in kreis_names."""
    import pandas as pd

    masks = []
    for kreis_name in kreis_names:
        # Exact match first, then partial
        exact = kreise_gdf["GEN"] == kreis_name
        if exact.any():
            masks.append(exact)
        else:
            partial = kreise_gdf["GEN"].str.contains(kreis_name, case=False, na=False)
            if partial.any():
                masks.append(partial)
            else:
                log.debug("[%s] No match for Kreis: %r", ils_id, kreis_name)

    if not masks:
        return kreise_gdf.iloc[0:0]  # empty GeoDataFrame

    combined = masks[0]
    for m in masks[1:]:
        combined = combined | m
    return kreise_gdf[combined]


def derive_bb(kreise_gdf) -> list[dict[str, Any]]:
    """Derive Brandenburg ILS polygons."""
    return derive("BB", kreise_gdf, _BB_ASSIGNMENTS)


def derive_bw(kreise_gdf) -> list[dict[str, Any]]:
    """Derive Baden-Württemberg ILS polygons."""
    return derive("BW", kreise_gdf, _BW_ASSIGNMENTS)


def _short(name: str) -> str:
    name = name.replace("Leitstelle ", "").strip()
    replacements = {"Ä": "AE", "Ö": "OE", "Ü": "UE", "ä": "ae", "ö": "oe", "ü": "ue", "ß": "SS"}
    result = name
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = "".join(c for c in result if c.isalnum())
    return result[:6].upper()
