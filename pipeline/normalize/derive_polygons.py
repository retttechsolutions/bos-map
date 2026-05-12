"""Derive ILS polygons from BKG VG250 administrative boundaries.

Used for states where no official polygon geodata service exists but the
legal assignment of Landkreise to Leitstellen is known.
"""

from __future__ import annotations

import logging
from typing import Any

log = logging.getLogger(__name__)

# 2-digit state code (SN_L field in VG250_KRS.shp)
_BL_SNL: dict[str, str] = {
    "SH": "01", "HH": "02", "NI": "03", "HB": "04",
    "NW": "05", "HE": "06", "RP": "07", "BW": "08",
    "BY": "09", "SL": "10", "BE": "11", "BB": "12",
    "MV": "13", "SN": "14", "ST": "15", "TH": "16",
}

# ── Brandenburg ───────────────────────────────────────────────────────────────
# Source: Regionalleitstellenverordnung Brandenburg (RettZEntV BB)
_BB_ASSIGNMENTS: dict[str, list[str]] = {
    "Leitstelle Nord": ["Prignitz", "Ostprignitz-Ruppin", "Oberhavel", "Havelland"],
    "Leitstelle Ost": ["Barnim", "Märkisch-Oderland", "Oder-Spree", "Frankfurt (Oder)"],
    "Leitstelle Süd": ["Dahme-Spreewald", "Teltow-Fläming", "Elbe-Elster", "Spree-Neiße", "Cottbus"],
    "Leitstelle West": ["Potsdam-Mittelmark", "Brandenburg an der Havel", "Potsdam"],
    "Leitstelle Lausitz": ["Oberspreewald-Lausitz"],
}

# ── Baden-Württemberg ─────────────────────────────────────────────────────────
# Source: Rettungsdienstgesetz BW – 35 Rettungsdienstbereiche (Landkreise)
_BW_ASSIGNMENTS: dict[str, list[str]] = {
    "Leitstelle Stuttgart":              ["Stuttgart"],
    "Leitstelle Böblingen":              ["Böblingen"],
    "Leitstelle Esslingen":              ["Esslingen"],
    "Leitstelle Göppingen":              ["Göppingen"],
    "Leitstelle Ludwigsburg":            ["Ludwigsburg"],
    "Leitstelle Waiblingen":             ["Rems-Murr-Kreis"],
    "Leitstelle Heidelberg":             ["Heidelberg", "Rhein-Neckar-Kreis"],
    "Leitstelle Mannheim":               ["Mannheim"],
    "Leitstelle Pforzheim":              ["Pforzheim", "Enzkreis", "Calw"],
    "Leitstelle Karlsruhe":              ["Karlsruhe", "Karlsruhe (Stadtkreis)"],
    "Leitstelle Rastatt":                ["Rastatt", "Baden-Baden"],
    "Leitstelle Heilbronn":              ["Heilbronn", "Heilbronn (Stadtkreis)"],
    "Leitstelle Schwäbisch Hall":        ["Schwäbisch Hall"],
    "Leitstelle Main-Tauber":            ["Main-Tauber-Kreis"],
    "Leitstelle Hohenlohe":              ["Hohenlohekreis"],
    "Leitstelle Heidenheim":             ["Heidenheim"],
    "Leitstelle Aalen":                  ["Ostalbkreis"],
    "Leitstelle Freiburg":               ["Freiburg im Breisgau"],
    "Leitstelle Breisgau-Hochschwarzwald": ["Breisgau-Hochschwarzwald"],
    "Leitstelle Emmendingen":            ["Emmendingen"],
    "Leitstelle Offenburg":              ["Ortenaukreis"],
    "Leitstelle Rottweil":               ["Rottweil"],
    "Leitstelle Schwarzwald-Baar":       ["Schwarzwald-Baar-Kreis"],
    "Leitstelle Tuttlingen":             ["Tuttlingen"],
    "Leitstelle Konstanz":               ["Konstanz"],
    "Leitstelle Lörrach":                ["Lörrach"],
    "Leitstelle Waldshut":               ["Waldshut"],
    "Leitstelle Reutlingen":             ["Reutlingen"],
    "Leitstelle Tübingen":               ["Tübingen"],
    "Leitstelle Zollernalbkreis":        ["Zollernalbkreis"],
    "Leitstelle Ulm":                    ["Ulm", "Alb-Donau-Kreis"],
    "Leitstelle Biberach":               ["Biberach"],
    "Leitstelle Bodenseekreis":          ["Bodenseekreis"],
    "Leitstelle Ravensburg":             ["Ravensburg"],
    "Leitstelle Sigmaringen":            ["Sigmaringen"],
    "Leitstelle Neckar-Odenwald":        ["Neckar-Odenwald-Kreis"],
    "Leitstelle Freudenstadt":           ["Freudenstadt"],
}

# ── Schleswig-Holstein ────────────────────────────────────────────────────────
# Source: RDG SH – 4 Integrierte Regionalleitstellen (IRLS)
_SH_ASSIGNMENTS: dict[str, list[str]] = {
    "IRLS Nord":  ["Flensburg", "Schleswig-Flensburg", "Nordfriesland"],
    "IRLS West":  ["Dithmarschen", "Steinburg", "Neumünster"],
    "IRLS Mitte": ["Kiel", "Rendsburg-Eckernförde", "Plön"],
    "IRLS Süd":   ["Lübeck", "Ostholstein", "Herzogtum Lauenburg", "Stormarn", "Pinneberg", "Segeberg"],
}

# ── Thüringen ─────────────────────────────────────────────────────────────────
# Source: ThürRettG – 8 Leitstellen (Stand 2024)
_TH_ASSIGNMENTS: dict[str, list[str]] = {
    "Leitstelle Erfurt":     ["Erfurt", "Gotha", "Ilm-Kreis", "Weimarer Land"],
    "Leitstelle Nordhausen": ["Nordhausen", "Eichsfeld", "Kyffhäuserkreis", "Unstrut-Hainich-Kreis"],
    "Leitstelle Weimar":     ["Weimar"],
    "Leitstelle Jena":       ["Jena", "Saale-Holzland-Kreis"],
    "Leitstelle Gera":       ["Gera", "Greiz", "Altenburger Land"],
    "Leitstelle Saalfeld":   ["Saalfeld-Rudolstadt", "Saale-Orla-Kreis"],
    "Leitstelle Suhl":       ["Suhl", "Schmalkalden-Meiningen", "Hildburghausen", "Sonneberg"],
    "Leitstelle Eisenach":   ["Eisenach", "Wartburgkreis"],
}


# ─────────────────────────────────────────────────────────────────────────────
# Generic helpers
# ─────────────────────────────────────────────────────────────────────────────

def _state_kreise(kreise_gdf, bl_code: str):
    """Filter VG250_KRS GeoDataFrame to Kreise of the given Bundesland."""
    snl = _BL_SNL[bl_code]
    if "SN_L" in kreise_gdf.columns:
        return kreise_gdf[kreise_gdf["SN_L"] == snl]
    if "AGS" in kreise_gdf.columns:
        return kreise_gdf[kreise_gdf["AGS"].str[:2] == snl]
    raise ValueError(f"VG250 GDF has neither SN_L nor AGS column for {bl_code}")


def _one_per_kreis(bl_code: str, kreise_gdf) -> list[dict[str, Any]]:
    """Create one ILS per Landkreis / kreisfreie Stadt (1:1 mapping)."""
    from normalize import geometry as geom_mod
    from normalize import schema as schema_mod

    state_kreise = _state_kreise(kreise_gdf, bl_code)
    # Keep only GF=4 (territory features) to avoid duplicate boundary entries
    if "GF" in state_kreise.columns:
        state_kreise = state_kreise[state_kreise["GF"] == 4]

    rows = list(state_kreise.iterrows())

    # First pass: detect short-code collisions (Stadt + Landkreis sharing a name)
    short_counts: dict[str, int] = {}
    for _, row in rows:
        short_counts[_short(str(row["GEN"]))] = short_counts.get(_short(str(row["GEN"])), 0) + 1

    results: list[dict] = []
    seen_ids: set[str] = set()
    for _, row in rows:
        kreis_name: str = str(row["GEN"])
        base_short = _short(kreis_name)

        if short_counts[base_short] > 1:
            # Disambiguate using BEZ (Bezeichnung) field
            bez = str(row.get("BEZ", "")).lower()
            suffix = "ST" if ("stadt" in bez or "bezirk" in bez) else "LK"
            short = base_short + suffix
        else:
            short = base_short

        ils_id = schema_mod.build_id(bl_code, short)
        if ils_id in seen_ids:
            log.warning("[%s] Doppelte ID übersprungen (AGS=%s)", ils_id, row.get("AGS", "?"))
            continue
        seen_ids.add(ils_id)

        try:
            processed_geom = geom_mod.process(row.geometry, ils_id)
        except Exception as exc:
            log.warning("[%s] Geometry error für %s: %s", ils_id, kreis_name, exc)
            processed_geom = None

        bez_label = str(row.get("BEZ", ""))
        result = schema_mod.canonical_feature(
            leitstellen_id=ils_id,
            leitstellenname=f"ILS {kreis_name}",
            bundesland=bl_code,
            geometry=processed_geom,
            quelltyp="recht_abgeleitet",
            geometry_basis="verwaltungsgrenze_abgeleitet",
            source_url=None,
            review_status="needs_review",
            bemerkung=f"1:1-Kreis-Mapping aus VG250: {bez_label} {kreis_name}".strip(),
        )
        results.append(result)
    log.info("%s: %d ILS aus VG250 Kreisen abgeleitet", bl_code, len(results))
    return results


def derive(
    bl_code: str,
    kreise_gdf,
    assignments: dict[str, list[str]],
) -> list[dict[str, Any]]:
    """Build canonical features from explicit Leitstelle→Kreise assignments."""
    from normalize import geometry as geom_mod
    from normalize import schema as schema_mod

    results: list[dict] = []
    for ils_name, kreis_names in assignments.items():
        ils_id = schema_mod.build_id(bl_code, _short(ils_name))
        matched = _match_kreise(kreise_gdf, kreis_names, ils_id)
        if matched.empty:
            log.warning("[%s] Keine Kreise gefunden für: %s", ils_id, kreis_names)
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
    log.info("%s: %d ILS aus Zuordnungstabelle abgeleitet", bl_code, len(results))
    return results


def _match_kreise(kreise_gdf, kreis_names: list[str], ils_id: str):
    import pandas as pd

    masks = []
    for kreis_name in kreis_names:
        exact = kreise_gdf["GEN"] == kreis_name
        if exact.any():
            masks.append(exact)
        else:
            partial = kreise_gdf["GEN"].str.contains(kreis_name, case=False, na=False)
            if partial.any():
                masks.append(partial)
            else:
                log.debug("[%s] Kein VG250-Match für Kreis: %r", ils_id, kreis_name)

    if not masks:
        return kreise_gdf.iloc[0:0]
    combined = masks[0]
    for m in masks[1:]:
        combined = combined | m
    return kreise_gdf[combined]


def _short(name: str) -> str:
    name = name.replace("Leitstelle ", "").replace("IRLS ", "").strip()
    replacements = {
        "Ä": "AE", "Ö": "OE", "Ü": "UE",
        "ä": "ae", "ö": "oe", "ü": "ue", "ß": "SS",
    }
    result = name
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = "".join(c for c in result if c.isalnum())
    return result[:6].upper()


# ── Public derive_* functions ─────────────────────────────────────────────────

def derive_bb(kreise_gdf) -> list[dict[str, Any]]:
    return derive("BB", kreise_gdf, _BB_ASSIGNMENTS)

def derive_bw(kreise_gdf) -> list[dict[str, Any]]:
    return derive("BW", kreise_gdf, _BW_ASSIGNMENTS)

def derive_sh(kreise_gdf) -> list[dict[str, Any]]:
    return derive("SH", kreise_gdf, _SH_ASSIGNMENTS)

def derive_th(kreise_gdf) -> list[dict[str, Any]]:
    return derive("TH", kreise_gdf, _TH_ASSIGNMENTS)

# 1:1 Kreis → ILS states
def derive_ni(kreise_gdf) -> list[dict[str, Any]]:
    return _one_per_kreis("NI", kreise_gdf)

def derive_he(kreise_gdf) -> list[dict[str, Any]]:
    return _one_per_kreis("HE", kreise_gdf)

def derive_mv(kreise_gdf) -> list[dict[str, Any]]:
    return _one_per_kreis("MV", kreise_gdf)

def derive_st(kreise_gdf) -> list[dict[str, Any]]:
    return _one_per_kreis("ST", kreise_gdf)

def derive_sl(kreise_gdf) -> list[dict[str, Any]]:
    return _one_per_kreis("SL", kreise_gdf)

def derive_rp(kreise_gdf) -> list[dict[str, Any]]:
    return _one_per_kreis("RP", kreise_gdf)

def derive_hh(kreise_gdf) -> list[dict[str, Any]]:
    return _one_per_kreis("HH", kreise_gdf)

def derive_hb(kreise_gdf) -> list[dict[str, Any]]:
    return _one_per_kreis("HB", kreise_gdf)

def derive_be(kreise_gdf) -> list[dict[str, Any]]:
    return _one_per_kreis("BE", kreise_gdf)

def derive_nw(kreise_gdf) -> list[dict[str, Any]]:
    """VG250 fallback for NRW (used when OGC API yields no features)."""
    return _one_per_kreis("NW", kreise_gdf)

def derive_by_fallback(kreise_gdf) -> list[dict[str, Any]]:
    """VG250 fallback for Bayern (used when WFS harvest fails)."""
    return _one_per_kreis("BY", kreise_gdf)
