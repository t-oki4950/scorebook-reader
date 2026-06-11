#!/usr/bin/env python3
"""Validate rule JSON files with the project JSON Schemas.

This validator supports the JSON Schema subset used in schemas/*.schema.json,
so the project can run without installing extra packages.
"""

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

VALIDATION_TARGETS = [
    ("rules/symbol_dictionary.json", "schemas/symbol_rule.schema.json"),
    ("rules/position_rules.json", "schemas/position_rule.schema.json"),
    ("rules/compound_rules.json", "schemas/compound_rule.schema.json"),
    ("examples/reading_examples.json", "schemas/reading_example.schema.json"),
]

TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


def load_json(relative_path):
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


def check_type(value, expected_type):
    if expected_type == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    return isinstance(value, TYPE_MAP[expected_type])


def validate_value(value, schema, path="$"):
    errors = []
    expected_type = schema.get("type")

    if expected_type and not check_type(value, expected_type):
        actual = type(value).__name__
        errors.append(f"{path}: type must be {expected_type}, got {actual}")
        return errors

    if "enum" in schema and value not in schema["enum"]:
        errors.append(f"{path}: value must be one of {schema['enum']}")

    if expected_type == "object":
        required = schema.get("required", [])
        for key in required:
            if key not in value:
                errors.append(f"{path}.{key}: required property is missing")

        properties = schema.get("properties", {})
        for key, child_value in value.items():
            child_schema = properties.get(key)
            if child_schema:
                errors.extend(validate_value(child_value, child_schema, f"{path}.{key}"))
            elif schema.get("additionalProperties") is False:
                errors.append(f"{path}.{key}: additional property is not allowed")

    if expected_type == "array":
        min_items = schema.get("minItems")
        if min_items is not None and len(value) < min_items:
            errors.append(f"{path}: must contain at least {min_items} item(s)")

        item_schema = schema.get("items")
        if item_schema:
            for index, item in enumerate(value):
                errors.extend(validate_value(item, item_schema, f"{path}[{index}]"))

    return errors


def validate_file(data_path, schema_path):
    data = load_json(data_path)
    schema = load_json(schema_path)
    return validate_value(data, schema, "$")


def main():
    all_errors = []
    for data_path, schema_path in VALIDATION_TARGETS:
        errors = validate_file(data_path, schema_path)
        if errors:
            all_errors.append((data_path, errors))
        else:
            print(f"OK: {data_path}")

    if all_errors:
        print("\n検証エラー:", file=sys.stderr)
        for data_path, errors in all_errors:
            print(f"\n{data_path}", file=sys.stderr)
            for error in errors:
                print(f"- {error}", file=sys.stderr)
        return 1

    print("\nすべてのルールJSONがスキーマに適合しています。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
