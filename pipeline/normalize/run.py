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

    # ── Bayern ──────────────────────────────────────────────────────────────
    by_raw = raw_dir / "by_wfs"
    if (by_raw / "by_ils_flaeche.geojson").exists():
        try:
            from harvest.by_wfs import normalize as by_normalize
            features = by_normalize(by_raw)
            _write(features, output_dir / "by.geojson")
        except Exception as exc:
            log.error("Bayern normalize failed: %s", exc)

    # ── NRW ─────────────────────────────────────────────────────────────────
    nrw_raw = raw_dir / "nrw_ogc"
    vg250_dir = raw_dir / "bkg_vg250" / "extracted"
    if (nrw_raw / "nrw_leitstellen.geojson").exists():
        try:
            from harvest.nrw_ogc import normalize as nrw_normalize
            features = nrw_normalize(nrw_raw, vg250_dir if vg250_dir.exists() else None)
            _write(features, output_dir / "nrw.geojson")
        except Exception as exc:
            log.error("NRW normalize failed: %s", exc)

    # ── Sachsen ──────────────────────────────────────────────────────────────
    sn_raw = raw_dir / "sn_wms"
    if sn_raw.exists():
        try:
            from harvest.sn_wms import normalize as sn_normalize
            features = sn_normalize(sn_raw)
            _write(features, output_dir / "sn.geojson")
        except Exception as exc:
            log.error("Sachsen normalize failed: %s", exc)

    # ── Admin-boundary derivations (BB, BW) ───────────────────────────────
    if vg250_dir.exists():
        try:
            from harvest.bkg_vg250 import load_kreise
            from normalize.derive_polygons import derive_bb, derive_bw
            kreise_gdf = load_kreise(vg250_dir)

            bb_features = derive_bb(kreise_gdf)
            if bb_features:
                _write(bb_features, output_dir / "bb.geojson")

            bw_features = derive_bw(kreise_gdf)
            if bw_features:
                _write(bw_features, output_dir / "bw.geojson")
        except Exception as exc:
            log.warning("Admin-boundary derivation failed: %s", exc)

    # ── Wikipedia bootstrap (remaining states) ────────────────────────────
    wiki_raw = raw_dir / "wikipedia"
    if (wiki_raw / "wikipedia_ils.json").exists():
        try:
            from harvest.wikipedia import normalize as wiki_normalize
            features = wiki_normalize(wiki_raw)
            _write(features, output_dir / "wikipedia.geojson")
        except Exception as exc:
            log.error("Wikipedia normalize failed: %s", exc)

    log.info("Normalization complete → %s", output_dir)


def _write(features: list[dict], path: Path) -> None:
    fc = {"type": "FeatureCollection", "features": features}
    path.write_text(json.dumps(fc, ensure_ascii=False), encoding="utf-8")
    log.info("Wrote %d features → %s", len(features), path.name)


if __name__ == "__main__":
    import argparse
    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--raw", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    run(Path(args.raw), Path(args.output))
