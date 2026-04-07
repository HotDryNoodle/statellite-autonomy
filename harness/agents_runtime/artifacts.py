"""Lightweight schema-backed artifact validation."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = REPO_ROOT / "harness" / "schemas"


def load_schema(name: str) -> dict[str, Any]:
    path = SCHEMA_DIR / f"{name}.schema.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _validate_value(value: Any, schema: dict[str, Any], path: str) -> list[str]:
    errors: list[str] = []
    expected_type = schema.get("type")
    if expected_type == "object":
        if not isinstance(value, dict):
            return [f"{path} must be an object"]
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key} is required")
        properties = schema.get("properties", {})
        for key, item in value.items():
            if key in properties:
                errors.extend(_validate_value(item, properties[key], f"{path}.{key}"))
    elif expected_type == "array":
        if not isinstance(value, list):
            return [f"{path} must be an array"]
        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                errors.extend(_validate_value(item, item_schema, f"{path}[{index}]"))
    elif expected_type == "string":
        if not isinstance(value, str):
            return [f"{path} must be a string"]
        min_length = schema.get("minLength")
        if min_length is not None and len(value) < min_length:
            errors.append(f"{path} must be at least {min_length} characters")
        choices = schema.get("enum")
        if choices is not None and value not in choices:
            errors.append(f"{path} must be one of {choices}")
    elif expected_type == "boolean":
        if not isinstance(value, bool):
            return [f"{path} must be a boolean"]
    elif expected_type == "integer":
        if not isinstance(value, int) or isinstance(value, bool):
            return [f"{path} must be an integer"]
    return errors


def validate_artifact_payload(name: str, payload: dict[str, Any]) -> list[str]:
    schema = load_schema(name)
    return _validate_value(payload, schema, "$")
