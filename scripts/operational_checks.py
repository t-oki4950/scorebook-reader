#!/usr/bin/env python3
"""Operational checks for corrected scorebook readings."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]

PITCH_SYMBOLS = {"ー", "-", "✗", "×", "二重✗", "✗✗", "××", "△", "B", "SK", "IP", "インプレー"}
NON_PITCH_SYMBOL_MARKERS = [
    "小さい",
    "Ⅰ",
    "Ⅱ",
    "Ⅲ",
    "中央l",
    "中央のl",
    "右下斜め二重線",
    "右下の斜め二重線",
    "マス目中央の●または塗りつぶし",
    "●",
    "塗りつぶし",
]


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def resolve_path(path):
    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def event_counts_as_pitch(event):
    if isinstance(event, dict):
        return bool(event.get("counts_as_pitch", True))
    return symbol_counts_as_pitch(str(event))


def symbol_counts_as_pitch(symbol):
    text = str(symbol).strip()
    if not text:
        return False
    if text in {"’", "'"}:
        return False
    if text == "WP":
        return False
    if any(marker in text for marker in NON_PITCH_SYMBOL_MARKERS):
        return False
    if "’" in text and "WP" in text:
        return any(pitch_symbol in text for pitch_symbol in PITCH_SYMBOLS)
    return text in PITCH_SYMBOLS


def count_independent_pitches(at_bat):
    pitch_events = at_bat.get("pitch_events")
    if pitch_events:
        return sum(1 for event in pitch_events if event_counts_as_pitch(event))
    return sum(1 for symbol in at_bat.get("symbols", []) if symbol_counts_as_pitch(symbol))


def sorted_at_bats(reading):
    return sorted(
        reading.get("at_bats", []),
        key=lambda at_bat: (at_bat.get("inning", 0), at_bat.get("batter_number", 0)),
    )


def validate_cumulative_pitch_counts(reading):
    errors = []
    previous_by_inning = {}
    for at_bat in sorted_at_bats(reading):
        inning = at_bat.get("inning")
        batter_number = at_bat.get("batter_number")
        cumulative = at_bat.get("cumulative_pitch_count")
        if cumulative is None:
            errors.append(f"{inning}回{batter_number}人目: 累計投球数が未入力です。")
            continue

        previous = previous_by_inning.get(inning, 0)
        pitch_count = count_independent_pitches(at_bat)
        expected = previous + pitch_count
        if cumulative != expected:
            errors.append(
                f"{inning}回{batter_number}人目: 前打者終了時の累計{previous} + "
                f"この打席の独立投球数{pitch_count} = {expected} のはずですが、"
                f"累計投球数は{cumulative}です。"
            )
        previous_by_inning[inning] = cumulative
    return errors


def has_symbol(at_bat, keyword):
    return any(keyword in str(symbol) for symbol in at_bat.get("symbols", []))


def has_third_out(at_bat):
    return (
        has_symbol(at_bat, "Ⅲ")
        or "3アウト" in str(at_bat.get("out_count", ""))
        or "3アウト" in str(at_bat.get("notes", ""))
    )


def has_inning_end_marker(at_bat):
    return (
        bool(at_bat.get("inning_end"))
        or has_symbol(at_bat, "右下斜め二重線")
        or has_symbol(at_bat, "右下の斜め二重線")
        or "攻撃終了" in str(at_bat.get("notes", ""))
    )


def validate_inning_end_detection(reading):
    errors = []
    for at_bat in sorted_at_bats(reading):
        inning = at_bat.get("inning")
        batter_number = at_bat.get("batter_number")
        third_out = has_third_out(at_bat)
        inning_end = has_inning_end_marker(at_bat)
        if third_out and not inning_end:
            errors.append(f"{inning}回{batter_number}人目: 3アウト目ですが、攻撃終了の印がありません。")
        if inning_end and not third_out:
            errors.append(f"{inning}回{batter_number}人目: 攻撃終了の印がありますが、3アウト目が確認できません。")
    return errors


def validate_reading(reading):
    errors = []
    errors.extend(validate_cumulative_pitch_counts(reading))
    errors.extend(validate_inning_end_detection(reading))
    return errors


def validate_reading_file(path):
    return validate_reading(load_json(resolve_path(path)))


def validate_json_file(path):
    try:
        load_json(resolve_path(path))
    except FileNotFoundError:
        return [f"{path}: ファイルが見つかりません。"]
    except json.JSONDecodeError as error:
        return [f"{path}: JSON形式が正しくありません。{error}"]
    return []


def collect_all_validation_errors(project_root=PROJECT_ROOT):
    root = Path(project_root)
    errors = []
    json_targets = [
        "rules/symbol_dictionary.json",
        "rules/position_rules.json",
        "rules/compound_rules.json",
        "examples/reading_examples.json",
        "outputs/provisional_reading.json",
        "outputs/corrected_reading.json",
        "examples/sample_game_001/provisional_reading.json",
        "examples/sample_game_001/corrected_reading.json",
    ]
    for relative_path in json_targets:
        errors.extend(validate_json_file(root / relative_path))

    for relative_path in [
        "outputs/corrected_reading.json",
        "examples/sample_game_001/corrected_reading.json",
    ]:
        path = root / relative_path
        if path.exists():
            reading = load_json(path)
            if reading.get("at_bats"):
                for error in validate_reading(reading):
                    errors.append(f"{relative_path}: {error}")
    return errors


def main():
    parser = argparse.ArgumentParser(description="実運用向けの読み取りデータ検証を実行します。")
    parser.add_argument(
        "--reading",
        default="examples/sample_game_001/corrected_reading.json",
        help="検証する読み取りJSON",
    )
    parser.add_argument("--all", action="store_true", help="プロジェクト内の主要JSONもまとめて検証する")
    args = parser.parse_args()

    errors = collect_all_validation_errors() if args.all else validate_reading_file(args.reading)
    if errors:
        print("検証エラー:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("実運用チェックはすべて成功しました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
