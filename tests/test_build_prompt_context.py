import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import build_prompt_context  # noqa: E402


def test_prompt_context_contains_sample_game_expected_fragments():
    markdown = build_prompt_context.build_markdown()
    expected_file = PROJECT_ROOT / "examples" / "sample_game_001" / "expected_prompt_context.md"
    expected_fragments = [
        line[2:].strip()
        for line in expected_file.read_text(encoding="utf-8").splitlines()
        if line.startswith("- ")
    ]

    missing = [fragment for fragment in expected_fragments if fragment not in markdown]
    assert missing == []
