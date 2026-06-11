import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import add_reading_example  # noqa: E402


def test_add_reading_example_from_corrected_file(tmp_path, monkeypatch):
    example_file = tmp_path / "reading_examples.json"
    example_file.write_text(
        json.dumps({"schema_version": "1.0", "examples": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    monkeypatch.setattr(add_reading_example, "EXAMPLE_FILE", example_file)

    corrected_file = PROJECT_ROOT / "examples" / "sample_game_001" / "corrected_reading.json"
    result = add_reading_example.main.__wrapped__ if hasattr(add_reading_example.main, "__wrapped__") else None
    assert result is None

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "add_reading_example.py",
            "--from-corrected",
            str(corrected_file),
            "--at-bat-id",
            "sample-game-001-inning1-batter5",
        ],
    )
    assert add_reading_example.main() == 0

    data = json.loads(example_file.read_text(encoding="utf-8"))
    assert data["examples"][0]["batting_result"] == "スクイズ成功、打者は一塁手によるタッチアウト"
    assert data["examples"][0]["out_count"] == "2アウト目"
