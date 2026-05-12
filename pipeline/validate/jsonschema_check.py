"""Validate ILS features against the canonical JSON Schema."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

import jsonschema

log = logging.getLogger(__name__)


def load_schema(schema_path: Path) -> dict:
    return json.loads(Path(schema_path).read_text("utf-8"))


def validate_feature(feature: dict, schema: dict) -> list[str]:
    """Return list of validation error messages (empty = valid)."""
    errors: list[str] = []
    validator = jsonschema.Draft202012Validator(schema)
    for error in validator.iter_errors(feature):
        errors.append(f"{'.'.join(str(p) for p in error.path)}: {error.message}")
    return errors


def validate_collection(
    features: list[dict],
    schema_path: Path,
    *,
    strict: bool = False,
) -> dict[str, list[str]]:
    """Validate every feature in a list.

    Returns a dict mapping leitstellen_id → list of error strings.
    Raises RuntimeError if strict=True and any errors are found.
    """
    schema = load_schema(schema_path)
    all_errors: dict[str, list[str]] = {}
    ids_seen: set[str] = set()

    for i, feat in enumerate(features):
        ils_id = feat.get("properties", {}).get("leitstellen_id", f"[index {i}]")
        errors = validate_feature(feat, schema)

        # Extra: duplicate ID check
        if ils_id in ids_seen:
            errors.append(f"Duplicate leitstellen_id: {ils_id}")
        ids_seen.add(ils_id)

        if errors:
            all_errors[ils_id] = errors
            for err in errors:
                log.warning("[%s] %s", ils_id, err)

    if strict and all_errors:
        count = sum(len(v) for v in all_errors.values())
        raise RuntimeError(f"Schema validation failed: {count} errors in {len(all_errors)} features")

    log.info("Validation complete: %d/%d features have errors", len(all_errors), len(features))
    return all_errors
