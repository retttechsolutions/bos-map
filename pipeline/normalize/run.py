"""Normalize pipeline: read raw harvested data and write per-state normalized GeoJSON files."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

log = logging.getLogger(__name__)


def run(raw_dir: Path, output_dir: Path) -> None:
    raw_dir = Path(raw_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    vg250_dir = raw_dir / "bkg_vg250" / "extracted"
    kreise_gdf = None
    if vg250_dir.exists():
        try:
            from harvest.bkg_vg250 import load_kreise
            kreise_gdf = load_kreise(vg250_dir)
            log.info("VG250 Kreise geladen: %d Einträge", len(kreise_gdf))
        except Exception as exc:
            log.error("VG250 laden fehlgeschlagen: %s", exc)

    # ── Bayern (WFS, mit VG250-Fallback) ─────────────────────────────────────
    by_raw = raw_dir / "by_wfs"
    if (by_raw / "by_ils_flaeche.geojson").exists():
        try:
            from harvest.by_wfs import normalize as by_normalize
            features = by_normalize(by_raw)
            if features:
                _write(features, output_dir / "by.geojson")
                log.info("Bayern: %d ILS aus WFS", len(features))
            elif kreise_gdf is not None:
                log.warning("Bayern WFS leer – VG250-Fallback")
                from normalize.derive_polygons import derive_by_fallback
                _write(derive_by_fallback(kreise_gdf), output_dir / "by.geojson")
        except Exception as exc:
            log.error("Bayern normalize fehlgeschlagen: %s", exc)
            if kreise_gdf is not None:
                try:
                    from normalize.derive_polygons import derive_by_fallback
                    _write(derive_by_fallback(kreise_gdf), output_dir / "by.geojson")
                except Exception as exc2:
                    log.error("Bayern VG250-Fallback fehlgeschlagen: %s", exc2)
    elif kreise_gdf is not None:
        log.info("Kein Bayern WFS – VG250-Fallback")
        try:
            from normalize.derive_polygons import derive_by_fallback
            _write(derive_by_fallback(kreise_gdf), output_dir / "by.geojson")
        except Exception as exc:
            log.error("Bayern VG250-Fallback fehlgeschlagen: %s", exc)

    # ── NRW (OGC API + VG250-Fallback) ───────────────────────────────────────
    nrw_raw = raw_dir / "nrw_ogc"
    nrw_features: list[dict] = []
    if (nrw_raw / "nrw_leitstellen.geojson").exists():
        try:
            from harvest.nrw_ogc import normalize as nrw_normalize
            nrw_features = nrw_normalize(nrw_raw, vg250_dir if vg250_dir.exists() else None)
        except Exception as exc:
            log.error("NRW OGC normalize fehlgeschlagen: %s", exc)

    if not nrw_features and kreise_gdf is not None:
        log.info("NRW OGC leer – VG250-Fallback (1:1 Kreis)")
        try:
            from normalize.derive_polygons import derive_nw
            nrw_features = derive_nw(kreise_gdf)
        except Exception as exc:
            log.error("NRW VG250-Fallback fehlgeschlagen: %s", exc)

    if nrw_features:
        _write(nrw_features, output_dir / "nw.geojson")

    # ── Sachsen (WFS, mit VG250-Fallback) ────────────────────────────────────
    sn_raw = raw_dir / "sn_wms"
    sn_features: list[dict] = []
    if sn_raw.exists():
        try:
            from harvest.sn_wms import normalize as sn_normalize
            sn_features = sn_normalize(sn_raw)
        except Exception as exc:
            log.error("Sachsen normalize fehlgeschlagen: %s", exc)

    if not sn_features and kreise_gdf is not None:
        log.info("Sachsen WFS leer – VG250-Fallback")
        try:
            from normalize.derive_polygons import _one_per_kreis
            sn_features = _one_per_kreis("SN", kreise_gdf)
        except Exception as exc:
            log.error("Sachsen VG250-Fallback fehlgeschlagen: %s", exc)

    if sn_features:
        _write(sn_features, output_dir / "sn.geojson")

    # ── VG250-Ableitungen (alle verbleibenden Bundesländer) ───────────────────
    if kreise_gdf is not None:
        from normalize.derive_polygons import (
            derive_bb, derive_bw, derive_sh, derive_th,
            derive_ni, derive_he, derive_mv, derive_st,
            derive_sl, derive_rp, derive_hh, derive_hb, derive_be,
        )
        vg250_states = [
            ("bb", derive_bb), ("bw", derive_bw), ("sh", derive_sh),
            ("th", derive_th), ("ni", derive_ni), ("he", derive_he),
            ("mv", derive_mv), ("st", derive_st), ("sl", derive_sl),
            ("rp", derive_rp), ("hh", derive_hh), ("hb", derive_hb),
            ("be", derive_be),
        ]
        for suffix, fn in vg250_states:
            out = output_dir / f"{suffix}.geojson"
            if out.exists():
                continue  # WFS/OGC-Ergebnis nicht überschreiben
            try:
                features = fn(kreise_gdf)
                if features:
                    _write(features, out)
            except Exception as exc:
                log.warning("%s VG250-Ableitung fehlgeschlagen: %s", suffix.upper(), exc)

    # ── Wikipedia-Bootstrap ───────────────────────────────────────────────────
    wiki_raw = raw_dir / "wikipedia"
    if (wiki_raw / "wikipedia_ils.json").exists():
        try:
            from harvest.wikipedia import normalize as wiki_normalize
            features = wiki_normalize(wiki_raw)
            if features:
                _write(features, output_dir / "wikipedia.geojson")
        except Exception as exc:
            log.error("Wikipedia normalize fehlgeschlagen: %s", exc)

    log.info("Normalisierung abgeschlossen → %s", output_dir)


def _write(features: list[dict], path: Path) -> None:
    fc = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    log.info("Geschrieben: %d Features → %s", len(features), path.name)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(Path(args.raw), Path(args.output))
