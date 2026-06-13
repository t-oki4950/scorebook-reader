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


def test_sample_game_cumulative_pitch_counts_are_continuous():
    reading = load_sample()
    assert operational_checks.validate_cumulative_pitch_counts(reading) == []


def test_simultaneous_event_is_not_counted_as_extra_pitch():
    reading = load_sample()
    batter3 = reading["at_bats"][2]
    assert batter3["symbols"][0] == "ー ’ WP"
    assert operational_checks.count_independent_pitches(batter3) == 4


def test_cumulative_pitch_count_error_is_reported_in_japanese():
    reading = copy.deepcopy(load_sample())
    reading["at_bats"][2]["cumulative_pitch_count"] = 13
    errors = operational_checks.validate_cumulative_pitch_counts(reading)
    assert errors
    assert "累計投球数" in errors[0]


def test_single_at_bat_reading_does_not_require_previous_context():
    reading = {
        "schema_version": "1.0",
        "status": "corrected",
        "at_bats": [
            {
                "inning": 1,
                "batter_number": 1,
                "symbols": ["✗らしき記載?", "ーらしき記載?", "6-3", "Ⅱ"],
                "pitch_sequence": ["✗", "ー"],
                "cumulative_pitch_count": 7,
            }
        ],
    }

    assert operational_checks.validate_cumulative_pitch_counts(reading) == []


def test_pitch_sequence_is_used_for_independent_pitch_count_when_present():
    at_bat = {
        "symbols": ["✗らしき記載?", "ーらしき記載?", "6-3", "Ⅱ"],
        "pitch_sequence": ["✗", "ー"],
    }

    assert operational_checks.count_independent_pitches(at_bat) == 2
