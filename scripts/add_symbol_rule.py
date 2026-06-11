#!/usr/bin/env python3
"""Add one symbol-reading rule to rules/symbol_dictionary.json."""

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
RULE_FILE = PROJECT_ROOT / "rules" / "symbol_dictionary.json"


def slugify(text):
    slug = re.sub(r"[^0-9A-Za-z]+", "-", text.strip()).strip("-").lower()
    return slug or "symbol"


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save_json(path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def split_csv(value):
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


def find_duplicates(rules, new_symbol, new_aliases, new_id):
    new_tokens = {new_symbol, *new_aliases}
    duplicates = []
    for rule in rules:
        existing_tokens = {rule.get("symbol", ""), *rule.get("aliases", [])}
        if rule.get("id") == new_id or new_tokens.intersection(existing_tokens):
            duplicates.append(rule)
    return duplicates


def main():
    parser = argparse.ArgumentParser(description="新しい単独記号ルールを追加します。")
    parser.add_argument("--symbol", required=True, help="記号。例: H")
    parser.add_argument("--reading", required=True, help="読み。例: ヒット")
    parser.add_argument("--category", default="未分類", help="分類。例: 打撃結果")
    parser.add_argument("--description", default="", help="補足説明")
    parser.add_argument("--aliases", default="", help="別表記をカンマ区切りで指定")
    parser.add_argument("--id", dest="rule_id", default="", help="ルールID。省略時は自動生成")
    parser.add_argument("--allow-duplicate", action="store_true", help="重複があっても追加する")
    args = parser.parse_args()

    data = load_json(RULE_FILE)
    rules = data.setdefault("rules", [])
    aliases = split_csv(args.aliases)
    rule_id = args.rule_id or f"symbol-{slugify(args.symbol)}"

    duplicates = find_duplicates(rules, args.symbol, aliases, rule_id)
    if duplicates:
        print("警告: 既存ルールと重複している可能性があります。", file=sys.stderr)
        for rule in duplicates:
            print(f"- {rule.get('id')}: {rule.get('symbol')} -> {rule.get('reading')}", file=sys.stderr)
        if not args.allow_duplicate:
            print("--allow-duplicate を付けると追加できます。", file=sys.stderr)
            return 1

    rules.append(
        {
            "id": rule_id,
            "symbol": args.symbol,
            "aliases": aliases,
            "category": args.category,
            "reading": args.reading,
            "description": args.description or args.reading,
        }
    )
    save_json(RULE_FILE, data)
    print(f"追加しました: {rule_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
