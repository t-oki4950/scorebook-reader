#!/usr/bin/env python3
"""Build Markdown context for a scorebook-reading AI prompt."""

import argparse
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]


def load_json(relative_path):
    return json.loads((PROJECT_ROOT / relative_path).read_text(encoding="utf-8"))


def bullet_list(items):
    return "\n".join(f"- {item}" for item in items)


def render_symbol_rules(data):
    lines = ["## 単独記号ルール", ""]
    for rule in data.get("rules", []):
        aliases = rule.get("aliases") or []
        alias_text = f" / 別表記: {', '.join(aliases)}" if aliases else ""
        lines.append(f"- `{rule['symbol']}`: {rule['reading']}（{rule['category']}）{alias_text}")
        if rule.get("description"):
            lines.append(f"  - 補足: {rule['description']}")
    return "\n".join(lines)


def render_position_rules(data):
    lines = ["## 位置ルール", ""]
    for rule in data.get("rules", []):
        lines.append(f"- {rule['cell_region']}: {rule['meaning']}")
        if rule.get("description"):
            lines.append(f"  - 補足: {rule['description']}")
    return "\n".join(lines)


def render_compound_rules(data):
    lines = ["## 複合ルール", ""]
    rules = sorted(data.get("rules", []), key=lambda rule: rule.get("priority", 0), reverse=True)
    for rule in rules:
        lines.append(f"### {rule['name']}")
        lines.append(f"- 優先度: {rule.get('priority', 0)}")
        lines.append("- 条件:")
        for condition in rule.get("conditions", []):
            lines.append(f"  - {condition}")
        lines.append(f"- 解釈: {rule['interpretation']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def render_examples(data):
    lines = ["## 読み取り事例", ""]
    for example in data.get("examples", []):
        title = f"{example['inning']}回{example['batter_number']}人目"
        lines.append(f"### {title}")
        lines.append(f"- 記号: {', '.join(example.get('symbols', []))}")
        lines.append(f"- 解釈: {', '.join(example.get('interpretations', []))}")
        if "cumulative_pitch_count" in example:
            lines.append(f"- 累計投球数: {example['cumulative_pitch_count']}")
        lines.append(f"- 打撃結果: {example['batting_result']}")
        if example.get("out_count"):
            lines.append(f"- アウトカウント: {example['out_count']}")
        if example.get("notes"):
            lines.append(f"- 備考: {example['notes']}")
        lines.append("")
    return "\n".join(lines).rstrip()


def build_markdown():
    symbol_rules = load_json("rules/symbol_dictionary.json")
    position_rules = load_json("rules/position_rules.json")
    compound_rules = load_json("rules/compound_rules.json")
    reading_examples = load_json("examples/reading_examples.json")

    sections = [
        "# スコアブック読解ルールコンテキスト",
        "",
        "以下は、草野球・軟式野球スコアブック画像を仮読み取りするための蓄積ルールです。",
        "AIはこの内容を優先し、曖昧な箇所は推測として明示してください。",
        "",
        render_symbol_rules(symbol_rules),
        "",
        render_position_rules(position_rules),
        "",
        render_compound_rules(compound_rules),
        "",
        render_examples(reading_examples),
        "",
    ]
    return "\n".join(sections)


def main():
    parser = argparse.ArgumentParser(description="AIに渡すMarkdown形式の読解コンテキストを生成します。")
    parser.add_argument("--output", help="出力先Markdown。省略時は標準出力")
    args = parser.parse_args()

    markdown = build_markdown()
    if args.output:
        output_path = Path(args.output)
        if not output_path.is_absolute():
            output_path = PROJECT_ROOT / output_path
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown, encoding="utf-8")
        print(f"生成しました: {output_path}")
    else:
        print(markdown)


if __name__ == "__main__":
    main()
