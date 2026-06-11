#!/usr/bin/env python3
"""Add one compound reading rule to rules/compound_rules.json."""

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RULE_FILE = PROJECT_ROOT / "rules" / "compound_rules.json"


def slugify(text):
    slug = re.sub(r"[^0-9A-Za-z]+", "-", text.strip()).strip("-").lower()
    return slug or "compound"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="複数の記号・位置・文脈からなる複合ルールを追加します。")
    parser.add_argument("--name", required=True, help="ルール名")
    parser.add_argument(
        "--condition",
        action="append",
        required=True,
        help="条件。複数ある場合は --condition を繰り返す",
    )
    parser.add_argument("--interpretation", required=True, help="成立時の解釈")
    parser.add_argument("--priority", type=int, default=50, help="優先度。大きいほど優先")
    parser.add_argument("--id", dest="rule_id", default="", help="ルールID。省略時は自動生成")
    parser.add_argument("--allow-duplicate", action="store_true", help="重複があっても追加する")
    args = parser.parse_args()

    data = load_json(RULE_FILE)
    rules = data.setdefault("rules", [])
    rule_id = args.rule_id or f"compound-{slugify(args.name)}"

    duplicates = [
        rule
        for rule in rules
        if rule.get("id") == rule_id
        or rule.get("name") == args.name
        or rule.get("conditions") == args.condition
    ]
    if duplicates:
        print("警告: 既存の複合ルールと重複している可能性があります。", file=sys.stderr)
        for rule in duplicates:
            print(f"- {rule.get('id')}: {rule.get('name')}", file=sys.stderr)
        if not args.allow_duplicate:
            print("--allow-duplicate を付けると追加できます。", file=sys.stderr)
            return 1

    rules.append(
        {
            "id": rule_id,
            "name": args.name,
            "conditions": args.condition,
            "interpretation": args.interpretation,
            "priority": args.priority,
        }
    )
    data["rules"] = sorted(rules, key=lambda rule: rule.get("priority", 0), reverse=True)
    save_json(RULE_FILE, data)
    print(f"追加しました: {rule_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
