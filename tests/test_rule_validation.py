import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import validate_rules  # noqa: E402


def test_rule_files_match_json_schemas():
    for data_path, schema_path in validate_rules.VALIDATION_TARGETS:
        errors = validate_rules.validate_file(data_path, schema_path)
        assert errors == []
