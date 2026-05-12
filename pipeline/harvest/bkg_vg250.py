"""Download BKG VG250 administrative boundary dataset (public domain, dl-de/zero-2-0).

VG250 provides authoritative Landkreis and Gemeinde boundaries for all of Germany.
Used to derive ILS polygons for states without official geodata services.
"""

from __future__ import annotations

import logging
import zipfile
from pathlib import Path

import httpx

log = logging.getLogger(__name__)

# BKG open data portal – VG250 (reference date 01.01. of current/last year)
# dl-de/zero-2-0 licence (public domain equivalent)
_VG250_URL = (
    "https://daten.gdz.bkg.bund.de/produkte/vg/vg250_ebenen_0101/"
    "aktuell/vg250_01-01.utm32s.shape.ebenen.zip"
)

# Layer files within the ZIP (Shapefile names for Landkreise and Gemeinden)
_EXPECTED_SHAPEFILES = {
    "VG250_KRS.shp",   # Kreise / Landkreise
    "VG250_GEM.shp",   # Gemeinden
    "VG250_LAN.shp",   # Länder
}


def download(output_dir: Path, force: bool = False) -> Path:
    """Download and extract VG250 ZIP to *output_dir*.

    Returns the path to the extracted directory containing the shapefiles.
    Skips download if already present (unless *force* is True).
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    zip_path = output_dir / "vg250.zip"
    extracted_dir = output_dir / "extracted"

    if extracted_dir.exists() and not force:
        existing = list(extracted_dir.rglob("VG250_KRS.shp"))
        if existing:
            log.info("VG250 already downloaded at %s", extracted_dir)
            return extracted_dir

    log.info("Downloading VG250 from BKG…")
    with httpx.Client(timeout=120, follow_redirects=True) as client:
        with client.stream("GET", _VG250_URL) as response:
            response.raise_for_status()
            with zip_path.open("wb") as f:
                for chunk in response.iter_bytes(chunk_size=65536):
                    f.write(chunk)

    log.info("Extracting VG250…")
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extracted_dir)

    zip_path.unlink()
    log.info("VG250 ready at %s", extracted_dir)
    return extracted_dir


def load_kreise(vg250_dir: Path):
    """Load Landkreise layer as a GeoDataFrame in WGS84."""
    import geopandas as gpd

    shp_files = list(Path(vg250_dir).rglob("VG250_KRS.shp"))
    if not shp_files:
        raise FileNotFoundError(f"VG250_KRS.shp not found under {vg250_dir}")
    gdf = gpd.read_file(shp_files[0])
    return gdf.to_crs("EPSG:4326")


def load_laender(vg250_dir: Path):
    """Load Bundesländer layer as a GeoDataFrame in WGS84."""
    import geopandas as gpd

    shp_files = list(Path(vg250_dir).rglob("VG250_LAN.shp"))
    if not shp_files:
        raise FileNotFoundError(f"VG250_LAN.shp not found under {vg250_dir}")
    gdf = gpd.read_file(shp_files[0])
    return gdf.to_crs("EPSG:4326")


if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    parser = argparse.ArgumentParser(description="Download BKG VG250")
    parser.add_argument("--output", required=True, help="Output directory")
    parser.add_argument("--force", action="store_true", help="Force re-download")
    args = parser.parse_args()
    download(Path(args.output), force=args.force)
