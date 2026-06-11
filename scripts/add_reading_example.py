#!/usr/bin/env python3
"""Add one corrected reading example to examples/reading_examples.json."""

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
EXAMPLE_FILE = PROJECT_ROOT / "examples" / "reading_examples.json"


def split_csv(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def default_id(inning, batter_number):
    return f"inning{inning}-batter{batter_number}"


def resolve_project_path(path_text):
    path = Path(path_text)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def find_corrected_at_bat(corrected_file, at_bat_id):
    corrected = load_json(corrected_file)
    for at_bat in corrected.get("at_bats", []):
        if at_bat.get("id") == at_bat_id:
            return at_bat
    raise ValueError(f"打席IDが見つかりません: {at_bat_id}")


def example_from_corrected(at_bat, example_id):
    required_fields = ["inning", "batter_number", "symbols", "interpretations", "batting_result"]
    missing = [field for field in required_fields if field not in at_bat]
    if missing:
        raise ValueError(f"修正済み打席に必須項目がありません: {', '.join(missing)}")

    example = {
        "id": example_id or at_bat.get("id") or default_id(at_bat["inning"], at_bat["batter_number"]),
        "inning": at_bat["inning"],
        "batter_number": at_bat["batter_number"],
        "symbols": at_bat["symbols"],
        "interpretations": at_bat["interpretations"],
        "batting_result": at_bat["batting_result"],
        "notes": at_bat.get("notes", ""),
    }
    if "cumulative_pitch_count" in at_bat:
        example["cumulative_pitch_count"] = at_bat["cumulative_pitch_count"]
    if at_bat.get("out_count"):
        example["out_count"] = at_bat["out_count"]
    return example


def example_from_args(args):
    missing = []
    for field in ["inning", "batter_number", "symbols", "interpretations", "batting_result"]:
        if getattr(args, field) in (None, ""):
            missing.append("--" + field.replace("_", "-"))
    if missing:
        raise ValueError(f"手入力で追加する場合は必須です: {', '.join(missing)}")

    example_id = args.example_id or default_id(args.inning, args.batter_number)
    example = {
        "id": example_id,
        "inning": args.inning,
        "batter_number": args.batter_number,
        "symbols": split_csv(args.symbols),
        "interpretations": split_csv(args.interpretations),
        "batting_result": args.batting_result,
        "notes": args.notes,
    }
    if args.cumulative_pitch_count is not None:
        example["cumulative_pitch_count"] = args.cumulative_pitch_count
    if args.out_count:
        example["out_count"] = args.out_count
    return example


def main():
    parser = argparse.ArgumentParser(description="人間が修正した読み取り事例を追加します。")
    parser.add_argument("--from-corrected", help="修正済み読み取りJSONから追加する。例: outputs/corrected_reading.json")
    parser.add_argument("--at-bat-id", help="--from-corrected で取り込む打席ID")
    parser.add_argument("--inning", type=int, help="イニング")
    parser.add_argument("--batter-number", type=int, help="その回の打者番号")
    parser.add_argument("--symbols", help="記号をカンマ区切りで指定")
    parser.add_argument("--interpretations", help="解釈をカンマ区切りで指定")
    parser.add_argument("--batting-result", help="打撃結果")
    parser.add_argument("--cumulative-pitch-count", type=int, help="累計投球数")
    parser.add_argument("--out-count", default="", help="アウトカウント。例: 2アウト目")
    parser.add_argument("--notes", default="", help="備考")
    parser.add_argument("--id", dest="example_id", default="", help="事例ID。省略時は自動生成")
    parser.add_argument("--allow-duplicate", action="store_true", help="同じIDがあっても追加する")
    args = parser.parse_args()

    try:
        if args.from_corrected:
            if not args.at_bat_id:
                raise ValueError("--from-corrected を使う場合は --at-bat-id も指定してください。")
            at_bat = find_corrected_at_bat(resolve_project_path(args.from_corrected), args.at_bat_id)
            example = example_from_corrected(at_bat, args.example_id)
        else:
            example = example_from_args(args)
    except ValueError as error:
        print(f"エラー: {error}", file=sys.stderr)
        return 1

    data = load_json(EXAMPLE_FILE)
    examples = data.setdefault("examples", [])
    example_id = example["id"]

    duplicates = [example for example in examples if example.get("id") == example_id]
    if duplicates:
        print("警告: 同じIDの読み取り事例が既にあります。", file=sys.stderr)
        for example in duplicates:
            print(f"- {example.get('id')}: {example.get('batting_result')}", file=sys.stderr)
        if not args.allow_duplicate:
            print("--allow-duplicate を付けると追加できます。", file=sys.stderr)
            return 1

    examples.append(example)
    save_json(EXAMPLE_FILE, data)
    print(f"追加しました: {example_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
