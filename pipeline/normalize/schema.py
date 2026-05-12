"""Map raw harvester fields to the canonical ILS GeoJSON feature schema."""

from __future__ import annotations

import re
from datetime import date
from typing import Any

# Two-letter codes for German Bundesländer
_BL_CODES = {
    "BB", "BE", "BW", "BY", "HB", "HE", "HH",
    "MV", "NI", "NW", "RP", "SH", "SL", "SN", "ST", "TH",
}

_QUELLTYP_VALUES = {"amtlich_wfs", "amtlich_ogcapi", "amtlich_html", "recht_abgeleitet", "community"}
_GEOMETRY_BASIS_VALUES = {"amtliche_grenze", "verwaltungsgrenze_abgeleitet", "digitalisiert", "community"}
_REVIEW_STATUS_VALUES = {"verified", "needs_review", "community"}


def build_id(bundesland: str, short: str) -> str:
    """Create a canonical leitstellen_id like DE-BY-ILS-MUE."""
    bl = bundesland.upper().strip()
    s = re.sub(r"[^A-Z0-9]", "", short.upper())
    return f"DE-{bl}-ILS-{s}"


def canonical_feature(
    *,
    leitstellen_id: str,
    leitstellenname: str,
    bundesland: str,
    geometry: dict | None,
    quelltyp: str,
    geometry_basis: str,
    source_url: str | None = None,
    source_crs: str | None = None,
    traeger: str | None = None,
    betreiber: str | None = None,
    adresse: str | None = None,
    telefon: str | None = None,
    notruf: str | None = None,
    funkgruppen: list[dict] | None = None,
    frequenzschema: str | None = None,
    valid_from: str | None = None,
    valid_to: str | None = None,
    review_status: str = "needs_review",
    bemerkung: str | None = None,
) -> dict[str, Any]:
    """Return a GeoJSON Feature dict conforming to the canonical schema."""
    if bundesland not in _BL_CODES:
        raise ValueError(f"Unknown Bundesland code: {bundesland!r}")
    if quelltyp not in _QUELLTYP_VALUES:
        raise ValueError(f"Invalid quelltyp: {quelltyp!r}")
    if geometry_basis not in _GEOMETRY_BASIS_VALUES:
        raise ValueError(f"Invalid geometry_basis: {geometry_basis!r}")
    if review_status not in _REVIEW_STATUS_VALUES:
        raise ValueError(f"Invalid review_status: {review_status!r}")

    return {
        "type": "Feature",
        "properties": {
            "leitstellen_id": leitstellen_id,
            "leitstellenname": leitstellenname.strip(),
            "bundesland": bundesland,
            "traeger": traeger,
            "betreiber": betreiber,
            "adresse": adresse,
            "telefon": telefon,
            "notruf": notruf,
            "quelltyp": quelltyp,
            "funkgruppen": funkgruppen or [],
            "frequenzschema": frequenzschema,
            "geometry_basis": geometry_basis,
            "source_url": source_url,
            "source_crs": source_crs,
            "valid_from": valid_from or date.today().isoformat(),
            "valid_to": valid_to,
            "review_status": review_status,
            "bemerkung": bemerkung,
        },
        "geometry": geometry,
    }


def funkgruppe(name: str, rolle: str, quelle: str, kurzwahl: str | None = None) -> dict:
    """Build a single Funkgruppe entry."""
    valid_rollen = {
        "Feuerwehr", "Rettungsdienst", "KatS", "Polizei", "THW",
        "Hilfsorganisation", "Pool", "DMO", "sonstige",
    }
    valid_quellen = {"landeskonzept", "amtlich", "community"}
    if rolle not in valid_rollen:
        raise ValueError(f"Invalid Funkgruppen-Rolle: {rolle!r}")
    if quelle not in valid_quellen:
        raise ValueError(f"Invalid Funkgruppen-Quelle: {quelle!r}")
    return {"name": name, "rolle": rolle, "quelle": quelle, "kurzwahl": kurzwahl}
