import copy
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import operational_checks  # noqa: E402


def load_sample():
    path = PROJECT_ROOT / "examples" / "sample_game_001" / "corrected_reading.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_sample_game_detects_valid_inning_end():
    reading = load_sample()
    assert operational_checks.validate_inning_end_detection(reading) == []


def test_third_out_without_inning_end_marker_is_error():
    reading = copy.deepcopy(load_sample())
    batter7 = reading["at_bats"][6]
    batter7["symbols"] = [symbol for symbol in batter7["symbols"] if symbol != "右下斜め二重線"]
    batter7["inning_end"] = False
    batter7["notes"] = ""

    errors = operational_checks.validate_inning_end_detection(reading)
    assert errors
    assert "攻撃終了の印がありません" in errors[0]
