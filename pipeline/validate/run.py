"""Validate pipeline: run all checks on the normalized feature collection."""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

from validate import coverage, jsonschema_check, topology

log = logging.getLogger(__name__)


def run(input_dir: Path, schema_path: Path, vg250_dir: Path | None = None) -> bool:
    """Run all validation checks. Returns True if all pass (warnings are ok)."""
    input_dir = Path(input_dir)
    schema_path = Path(schema_path)

    all_features: list[dict] = []
    for geojson_file in sorted(input_dir.glob("*.geojson")):
        data = json.loads(geojson_file.read_text("utf-8"))
        all_features.extend(data.get("features", []))

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
    parser.add_argument("--input", required=True, help="Directory of normalized GeoJSON files")
    parser.add_argument("--schema", required=True, help="Path to feature.schema.json")
    parser.add_argument("--vg250", help="Path to VG250 extracted directory (optional)")
    args = parser.parse_args()

    ok = run(Path(args.input), Path(args.schema), Path(args.vg250) if args.vg250 else None)
    sys.exit(0 if ok else 1)
