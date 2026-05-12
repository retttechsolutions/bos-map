"""Validate pipeline: run all checks on the normalized feature collection."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from validate import coverage, jsonschema_check, topology

log = logging.getLogger(__name__)


def run(
    schema_path: Path,
    input_dir: Path | None = None,
    merged_file: Path | None = None,
    vg250_dir: Path | None = None,
) -> bool:
    """Run all validation checks. Returns True if all pass (warnings are ok).

    Pass either *merged_file* (single merged GeoJSON) or *input_dir* (directory
    of per-state GeoJSON files). When using *input_dir* the deduplication that
    build/merge.py performs has not yet run, so duplicate-ID warnings are expected.
    """
    schema_path = Path(schema_path)

    all_features: list[dict] = []
    if merged_file is not None:
        data = json.loads(Path(merged_file).read_text("utf-8"))
        all_features = data.get("features", [])
    elif input_dir is not None:
        for geojson_file in sorted(Path(input_dir).glob("*.geojson")):
            data = json.loads(geojson_file.read_text("utf-8"))
            all_features.extend(data.get("features", []))
    else:
        raise ValueError("Either --input or --merged must be provided")

    if not all_features:
        log.warning("No features found in %s", input_dir)
        return False

    log.info("Validating %d features…", len(all_features))
    passed = True

    # 1. JSON Schema
    schema_errors = jsonschema_check.validate_collection(all_features, schema_path, strict=False)
    if schema_errors:
        log.error("JSON Schema errors in %d features", len(schema_errors))
        passed = False

    # 2. Topology
    topo_errors = topology.validate_all(all_features)
    if topo_errors:
        log.error("Topology errors in %d features", len(topo_errors))
        passed = False

    # 3. Count coverage per Bundesland
    count_warnings = coverage.check_counts(all_features)
    if count_warnings:
        log.warning("Count warnings for %d Bundesländer", len(count_warnings))

    # 4. Area coverage (optional)
    coverage.check_coverage(all_features, vg250_dir)

    return passed


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Validate normalized ILS features")
    parser.add_argument("--input", help="Directory of normalized GeoJSON files")
    parser.add_argument("--merged", help="Single merged ils.geojson (preferred; avoids cross-file duplicates)")
    parser.add_argument("--schema", required=True, help="Path to feature.schema.json")
    parser.add_argument("--vg250", help="Path to VG250 extracted directory (optional)")
    args = parser.parse_args()

    ok = run(
        schema_path=Path(args.schema),
        input_dir=Path(args.input) if args.input else None,
        merged_file=Path(args.merged) if args.merged else None,
        vg250_dir=Path(args.vg250) if args.vg250 else None,
    )
    sys.exit(0 if ok else 1)
