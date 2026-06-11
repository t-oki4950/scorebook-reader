#!/usr/bin/env python3
"""Add one cell-position rule to rules/position_rules.json."""

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RULE_FILE = PROJECT_ROOT / "rules" / "position_rules.json"


def slugify(text):
    slug = re.sub(r"[^0-9A-Za-z]+", "-", text.strip()).strip("-").lower()
    return slug or "position"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="マスの位置と意味の対応ルールを追加します。")
    parser.add_argument("--cell-region", required=True, help="マス内の位置。例: 正方形の右下")
    parser.add_argument("--meaning", required=True, help="意味。例: 1塁到達")
    parser.add_argument("--description", default="", help="補足説明")
    parser.add_argument("--id", dest="rule_id", default="", help="ルールID。省略時は自動生成")
    parser.add_argument("--allow-duplicate", action="store_true", help="重複があっても追加する")
    args = parser.parse_args()

    data = load_json(RULE_FILE)
    rules = data.setdefault("rules", [])
    rule_id = args.rule_id or f"position-{slugify(args.cell_region)}"

    duplicates = [
        rule
        for rule in rules
        if rule.get("id") == rule_id or rule.get("cell_region") == args.cell_region
    ]
    if duplicates:
        print("警告: 既存の位置ルールと重複している可能性があります。", file=sys.stderr)
        for rule in duplicates:
            print(f"- {rule.get('id')}: {rule.get('cell_region')} -> {rule.get('meaning')}", file=sys.stderr)
        if not args.allow_duplicate:
            print("--allow-duplicate を付けると追加できます。", file=sys.stderr)
            return 1

    rules.append(
        {
            "id": rule_id,
            "cell_region": args.cell_region,
            "meaning": args.meaning,
            "description": args.description or args.meaning,
        }
    )
    save_json(RULE_FILE, data)
    print(f"追加しました: {rule_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
