.PHONY: all install harvest normalize validate build clean test

PYTHON := python
DATA_DIR := ../data
RAW_DIR := $(DATA_DIR)/raw
PROCESSED_DIR := $(DATA_DIR)/processed
DOCS_DIR := ../docs

all: harvest normalize validate build

install:
	pip install -e ".[dev]"

# ── Harvesting ────────────────────────────────────────────────────────────────

harvest: harvest-bkg harvest-by harvest-nrw harvest-sn harvest-wikipedia

harvest-bkg:
	$(PYTHON) -m harvest.bkg_vg250 --output $(RAW_DIR)/bkg_vg250/

harvest-by:
	$(PYTHON) -m harvest.by_wfs --output $(RAW_DIR)/by_wfs/

harvest-nrw:
	$(PYTHON) -m harvest.nrw_ogc --output $(RAW_DIR)/nrw_ogc/

harvest-sn:
	$(PYTHON) -m harvest.sn_wms --output $(RAW_DIR)/sn_wms/

harvest-wikipedia:
	$(PYTHON) -m harvest.wikipedia --output $(RAW_DIR)/wikipedia/

# ── Normalize ─────────────────────────────────────────────────────────────────

normalize:
	$(PYTHON) -m normalize.run \
		--raw $(RAW_DIR) \
		--output $(PROCESSED_DIR)/normalized/

# ── Validate ──────────────────────────────────────────────────────────────────

validate:
	$(PYTHON) -m validate.run \
		--input $(PROCESSED_DIR)/normalized/ \
		--schema $(DATA_DIR)/schema/feature.schema.json

# ── Build ─────────────────────────────────────────────────────────────────────

build:
	$(PYTHON) -m build.run \
		--input $(PROCESSED_DIR)/normalized/ \
		--processed $(PROCESSED_DIR)/ \
		--docs $(DOCS_DIR)/

# ── Tests ─────────────────────────────────────────────────────────────────────

test:
	pytest tests/ -v

# ── Cleanup ───────────────────────────────────────────────────────────────────

clean:
	rm -rf $(PROCESSED_DIR)/normalized/
	find . -type d -name __pycache__ -exec rm -rf {} +
