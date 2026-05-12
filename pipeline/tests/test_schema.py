"""Tests for schema mapping and JSON Schema validation."""

import pytest

from normalize.schema import build_id, canonical_feature, funkgruppe
from validate.jsonschema_check import validate_feature


def _minimal_feature(**overrides):
    defaults = dict(
        leitstellen_id="DE-BY-ILS-MUE",
        leitstellenname="ILS München",
        bundesland="BY",
        geometry=None,
        quelltyp="amtlich_wfs",
        geometry_basis="amtliche_grenze",
        review_status="verified",
    )
    defaults.update(overrides)
    return canonical_feature(**defaults)


def test_build_id_basic():
    assert build_id("BY", "MUE") == "DE-BY-ILS-MUE"


def test_build_id_strips_special_chars():
    # build_id strips non-ASCII chars; umlaut expansion is the harvester's responsibility
    assert build_id("NW", "Böchum") == "DE-NW-ILS-BCHUM"


def test_canonical_feature_valid():
    feat = _minimal_feature()
    assert feat["type"] == "Feature"
    assert feat["properties"]["leitstellen_id"] == "DE-BY-ILS-MUE"
    assert feat["properties"]["bundesland"] == "BY"
    assert feat["properties"]["funkgruppen"] == []


def test_canonical_feature_invalid_bundesland():
    with pytest.raises(ValueError, match="Unknown Bundesland"):
        _minimal_feature(bundesland="XX")


def test_canonical_feature_invalid_quelltyp():
    with pytest.raises(ValueError, match="Invalid quelltyp"):
        _minimal_feature(quelltyp="made_up")


def test_funkgruppe_valid():
    fg = funkgruppe("M_Fw", "Feuerwehr", "landeskonzept", kurzwahl="12345")
    assert fg["name"] == "M_Fw"
    assert fg["rolle"] == "Feuerwehr"
    assert fg["kurzwahl"] == "12345"


def test_funkgruppe_invalid_rolle():
    with pytest.raises(ValueError, match="Invalid Funkgruppen-Rolle"):
        funkgruppe("X", "Falsch", "landeskonzept")


def test_schema_validation_passes(tmp_path):
    import json
    schema_path = tmp_path / "schema.json"
    # Use the actual schema
    import pathlib
    actual_schema = pathlib.Path(__file__).parents[2] / "data/schema/feature.schema.json"
    if not actual_schema.exists():
        pytest.skip("Schema file not found")
    feat = _minimal_feature()
    schema = json.loads(actual_schema.read_text("utf-8"))
    errors = validate_feature(feat, schema)
    assert errors == [], f"Unexpected validation errors: {errors}"


def test_schema_validation_fails_missing_required(tmp_path):
    import json
    import pathlib
    actual_schema = pathlib.Path(__file__).parents[2] / "data/schema/feature.schema.json"
    if not actual_schema.exists():
        pytest.skip("Schema file not found")
    feat = {"type": "Feature", "properties": {}, "geometry": None}
    schema = json.loads(actual_schema.read_text("utf-8"))
    errors = validate_feature(feat, schema)
    assert len(errors) > 0
