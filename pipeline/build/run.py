"""Build pipeline: merge normalized features, generate all output artefacts."""

from __future__ import annotations

import json
import logging
import shutil
import sys
from pathlib import Path

from build import merge as merge_mod
from build import points as points_mod
from build import spatial_index as index_mod
from build import static_api as api_mod

log = logging.getLogger(__name__)


def run(input_dir: Path, processed_dir: Path, docs_dir: Path) -> None:
    """Full build: merge → points → index → static API → copy to docs."""
    input_dir = Path(input_dir)
    processed_dir = Path(processed_dir)
    docs_dir = Path(docs_dir)

    # 1. Merge all normalized state files
    ils_geojson = processed_dir / "ils.geojson"
    features = merge_mod.merge(input_dir, ils_geojson)

    # 2. Extract centroids
    ils_points = processed_dir / "ils-points.geojson"
    points_mod.build_points(features, ils_points)

    # 3. Build spatial index
    ils_index = processed_dir / "ils-index.json"
    index_mod.build_index(features, ils_index)

    # 4. Build metadata
    api_mod.build_metadata(features, processed_dir / "metadata.json")

    # 5. Copy processed files to docs/data/
    docs_data_dir = docs_dir / "data"
    docs_data_dir.mkdir(parents=True, exist_ok=True)
    for src in [ils_geojson, ils_points, ils_index, processed_dir / "metadata.json"]:
        if src.exists():
            shutil.copy2(src, docs_data_dir / src.name)
            log.info("Copied %s → docs/data/", src.name)

    # 6. Build static API files
    api_dir = docs_dir / "api" / "v1"
    api_mod.build_api(features, api_dir)

    log.info("Build complete. %d ILS in docs/", len(features))


if __name__ == "__main__":
    import argparse

    logging.basicConfig(level=logging.INFO, stream=sys.stderr,
                        format="%(levelname)s %(name)s: %(message)s")
    parser = argparse.ArgumentParser(description="Build BOS-Map output artefacts")
    parser.add_argument("--input", required=True, help="Normalized GeoJSON directory")
    parser.add_argument("--processed", required=True, help="data/processed/ directory")
    parser.add_argument("--docs", required=True, help="docs/ directory")
    args = parser.parse_args()
    run(Path(args.input), Path(args.processed), Path(args.docs))
