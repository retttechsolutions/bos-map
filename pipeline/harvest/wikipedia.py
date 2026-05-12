"""Scrape the Wikipedia list of all German ILS as a bootstrap directory.

Source: Wikipedia "Liste der BOS-Leitstellen"
Licence: CC BY-SA (Wikipedia community)
Usage: bootstrap / reference only – all entries are flagged review_status="community"
"""

from __future__ import annotations

import json
import logging
import re
import time
from pathlib import Path
from typing import Any

import httpx
from bs4 import BeautifulSoup

log = logging.getLogger(__name__)

# Primary: the actual list article; fallback: general ILS article
_WIKI_URL = "https://de.wikipedia.org/wiki/Liste_der_BOS-Leitstellen"
_WIKI_URL_FALLBACK = "https://de.wikipedia.org/wiki/Integrierte_Leitstelle"

# Map Wikipedia section headings to Bundesland codes
_BL_MAPPING: dict[str, str] = {
    "Baden-Württemberg": "BW",
    "Bayern": "BY",
    "Berlin": "BE",
    "Brandenburg": "BB",
    "Bremen": "HB",
    "Hamburg": "HH",
    "Hessen": "HE",
    "Mecklenburg-Vorpommern": "MV",
    "Niedersachsen": "NI",
    "Nordrhein-Westfalen": "NW",
    "Rheinland-Pfalz": "RP",
    "Saarland": "SL",
    "Sachsen": "SN",
    "Sachsen-Anhalt": "ST",
    "Schleswig-Holstein": "SH",
    "Thüringen": "TH",
}

_MAX_RETRIES = 2


def _fetch_html(url: str) -> str:
    delay = 2.0
    last_exc: Exception | None = None
    headers = {"User-Agent": "BOS-Map/0.1 (https://github.com/retttechsolutions/bos-map; open data project)"}
    for attempt in range(1, _MAX_RETRIES + 1):
        try:
            with httpx.Client(timeout=30, follow_redirects=True, headers=headers) as client:
                resp = client.get(url)
                resp.raise_for_status()
                return resp.text
        except Exception as exc:
            last_exc = exc
            log.warning("Wikipedia fetch attempt %d failed: %s", attempt, exc)
            time.sleep(delay)
            delay *= 2
    raise RuntimeError("Wikipedia fetch failed") from last_exc


def harvest(output_dir: Path, force: bool = False) -> Path:
    """Scrape Wikipedia ILS list and save as JSON to *output_dir*."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    out_path = output_dir / "wikipedia_ils.json"

    if out_path.exists() and not force:
        log.info("Wikipedia data already harvested at %s", out_path)
        return out_path

    log.info("Fetching Wikipedia ILS list…")
    html: str | None = None
    for url in (_WIKI_URL, _WIKI_URL_FALLBACK):
        try:
            html = _fetch_html(url)
            log.info("Wikipedia: fetched from %s", url)
            break
        except Exception as exc:
            log.warning("Wikipedia URL %s failed: %s – trying next", url, exc)

    if html is None:
        log.warning(
            "All Wikipedia URLs failed. Writing empty placeholder. "
            "Pipeline will continue with official sources only."
        )
        out_path.write_text(json.dumps([], ensure_ascii=False), encoding="utf-8")
        return out_path

    entries = _parse(html)
    out_path.write_text(json.dumps(entries, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("Wikipedia: saved %d entries → %s", len(entries), out_path)
    return out_path


def _parse(html: str) -> list[dict]:
    soup = BeautifulSoup(html, "lxml")
    entries: list[dict] = []
    current_bl: str | None = None

    for element in soup.find_all(["h2", "h3", "table"]):
        if element.name in ("h2", "h3"):
            heading_text = element.get_text(strip=True)
            for bl_name, bl_code in _BL_MAPPING.items():
                if bl_name.lower() in heading_text.lower():
                    current_bl = bl_code
                    break
            continue

        if element.name == "table" and current_bl:
            rows = element.find_all("tr")
            if not rows:
                continue

            # Detect header row
            headers = [th.get_text(strip=True).lower() for th in rows[0].find_all(["th", "td"])]

            for row in rows[1:]:
                cells = row.find_all(["td", "th"])
                if not cells:
                    continue
                cell_texts = [c.get_text(strip=True) for c in cells]
                if len(cell_texts) < 2:
                    continue

                entry: dict[str, Any] = {"bundesland": current_bl}

                # Heuristic column mapping
                for i, (header, text) in enumerate(zip(headers, cell_texts)):
                    if not text:
                        continue
                    if any(k in header for k in ("name", "bezeichnung", "leitstelle", "ils")):
                        entry["name"] = text
                    elif any(k in header for k in ("standort", "ort", "sitz", "stadt")):
                        entry["standort"] = text
                    elif any(k in header for k in ("träger", "traeger")):
                        entry["traeger"] = text
                    elif any(k in header for k in ("betreiber",)):
                        entry["betreiber"] = text
                    elif any(k in header for k in ("zuständig", "bereich", "gebiet", "landkreis", "kreis")):
                        entry["zustaendigkeitsbereich"] = text
                    elif any(k in header for k in ("fläche", "flaeche", "km")):
                        entry["flaeche_km2"] = text
                    elif any(k in header for k in ("einwohner",)):
                        entry["einwohner"] = text
                    elif any(k in header for k in ("telefon", "tel.", "notruf")):
                        entry["telefon"] = text
                    elif any(k in header for k in ("adresse", "anschrift")):
                        entry["adresse"] = text
                    elif "anmerkung" in header or "bemerkung" in header or "hinweis" in header:
                        entry["bemerkung"] = text

                if "name" not in entry and cell_texts:
                    entry["name"] = cell_texts[0]

                if entry.get("name"):
                    entries.append(entry)

    return entries


def normalize(output_dir: Path) -> list[dict[str, Any]]:
    """Read Wikipedia data and return canonical ILS feature stubs (no geometry)."""
    from normalize import schema as schema_mod

    raw_path = Path(output_dir) / "wikipedia_ils.json"
    if not raw_path.exists():
        raise FileNotFoundError(f"Run harvest first: {raw_path}")

    entries = json.loads(raw_path.read_text("utf-8"))
    results: list[dict] = []

    for entry in entries:
        name = entry.get("name", "").strip()
        bl = entry.get("bundesland", "")
        if not name or not bl:
            continue

        # Clean up Wikipedia formatting artefacts
        name = re.sub(r"\[.*?\]", "", name).strip()
        if not name:
            continue

        short = _wiki_short(name, bl)
        ils_id = schema_mod.build_id(bl, short)

        # Combine address fields
        adresse = entry.get("adresse") or entry.get("standort")

        # Build bemerkung from coverage area + original note
        bereich = entry.get("zustaendigkeitsbereich", "")
        note = entry.get("bemerkung", "")
        bemerkung_parts = [p for p in [bereich, note] if p]
        bemerkung = " | ".join(bemerkung_parts) if bemerkung_parts else None

        result = schema_mod.canonical_feature(
            leitstellen_id=ils_id,
            leitstellenname=name,
            bundesland=bl,
            geometry=None,
            quelltyp="community",
            geometry_basis="community",
            source_url=_WIKI_URL,
            traeger=entry.get("traeger"),
            betreiber=entry.get("betreiber"),
            adresse=adresse,
            telefon=entry.get("telefon"),
            bemerkung=bemerkung,
            review_status="community",
        )
        results.append(result)

    log.info("Wikipedia: normalized %d ILS stubs", len(results))
    return results


def _wiki_short(name: str, bl: str) -> str:
    # Remove common prefixes
    name = re.sub(r"^(ILS|Leitstelle|Rettungsleitstelle|Feuerwehr-?leitstelle)\s+", "", name, flags=re.I)
    replacements = {"Ä": "AE", "Ö": "OE", "Ü": "UE", "ä": "ae", "ö": "oe", "ü": "ue", "ß": "SS"}
    result = name
    for old, new in replacements.items():
        result = result.replace(old, new)
    result = "".join(c for c in result if c.isalnum())
    return result[:6].upper()


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    parser = argparse.ArgumentParser(description="Scrape Wikipedia ILS list")
    parser.add_argument("--output", required=True)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()
    harvest(Path(args.output), force=args.force)
