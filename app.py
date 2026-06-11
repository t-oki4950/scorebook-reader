import base64
import binascii
import html
import json
import mimetypes
import re
import sys
from copy import deepcopy
from datetime import datetime
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


PROJECT_ROOT = Path(__file__).resolve().parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import operational_checks  # noqa: E402
import validate_rules  # noqa: E402
from build_prompt_context import build_markdown  # noqa: E402

INPUT_IMAGE_DIR = PROJECT_ROOT / "inputs" / "images"
PROVISIONAL_FILE = PROJECT_ROOT / "outputs" / "provisional_reading.json"
CORRECTED_FILE = PROJECT_ROOT / "outputs" / "corrected_reading.json"
READING_EXAMPLES_FILE = PROJECT_ROOT / "examples" / "reading_examples.json"
SYMBOL_RULES_FILE = PROJECT_ROOT / "rules" / "symbol_dictionary.json"
COMPOUND_RULES_FILE = PROJECT_ROOT / "rules" / "compound_rules.json"
PROMPT_CONTEXT_FILE = PROJECT_ROOT / "outputs" / "prompt_context.md"
CODEX_READING_REQUEST_FILE = PROJECT_ROOT / "outputs" / "codex_reading_request.md"
SAMPLE_GAME_DIR = PROJECT_ROOT / "examples" / "sample_game_001"
SAMPLE_PROVISIONAL_FILE = SAMPLE_GAME_DIR / "provisional_reading.json"
SAMPLE_CORRECTED_FILE = SAMPLE_GAME_DIR / "corrected_reading.json"
PASTE_COMPONENT_DIR = PROJECT_ROOT / "components" / "paste_image"

MAX_IMAGE_PREVIEW_HEIGHT = 640
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".tif", ".tiff", ".svg"}
IMAGE_UPLOAD_TYPES = ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tif", "tiff", "svg"]
MIME_TO_SUFFIX = {
    "image/png": ".png",
    "image/jpeg": ".jpg",
    "image/webp": ".webp",
    "image/gif": ".gif",
    "image/bmp": ".bmp",
    "image/tiff": ".tiff",
    "image/svg+xml": ".svg",
}


st.set_page_config(page_title="Scorebook Reader", layout="wide")
paste_image_component = components.declare_component("paste_image", path=str(PASTE_COMPONENT_DIR))


def load_json(path, fallback):
    if not path.exists():
        return deepcopy(fallback)
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        st.error(f"{path.name} のJSONを読めません: {error}")
        return deepcopy(fallback)


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def split_lines(value):
    return [line.strip() for line in value.splitlines() if line.strip()]


def split_csv(value):
    return [item.strip() for item in value.split(",") if item.strip()]


def join_list(values):
    if not values:
        return ""
    return "\n".join(str(value) for value in values)


def format_cell_value(value):
    if isinstance(value, list):
        return "\n".join(str(item) for item in value)
    if isinstance(value, dict):
        return json.dumps(value, ensure_ascii=False, sort_keys=True)
    if value is None:
        return ""
    return str(value)


def slugify(text, fallback):
    slug = re.sub(r"[^0-9A-Za-z]+", "-", text.strip()).strip("-").lower()
    return slug or fallback


def make_image_filename(original_name):
    original_path = Path(original_name or "scorebook-image.png")
    suffix = original_path.suffix.lower()
    if suffix not in IMAGE_EXTENSIONS:
        suffix = ".png"
    stem = slugify(original_path.stem, "scorebook-image")[:48]
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    return f"{timestamp}-{stem}{suffix}"


def make_pasted_image_filename(mime_type):
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = MIME_TO_SUFFIX.get(mime_type, ".png")
    return f"{timestamp}-pasted-scorebook{suffix}"


def save_uploaded_image(uploaded_file):
    INPUT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    filename = make_image_filename(getattr(uploaded_file, "name", "scorebook-image.png"))
    destination = INPUT_IMAGE_DIR / filename
    destination.write_bytes(uploaded_file.getvalue())
    return destination


def save_pasted_image(payload):
    data_url = payload.get("data_url", "")
    if "," not in data_url:
        raise ValueError("貼り付け画像のデータ形式を読み取れません。")
    header, encoded = data_url.split(",", 1)
    mime_type = payload.get("type") or header.removeprefix("data:").split(";", 1)[0]
    filename = make_pasted_image_filename(mime_type)
    destination = INPUT_IMAGE_DIR / filename
    INPUT_IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(base64.b64decode(encoded))
    return destination


def uploaded_file_signature(uploaded_file):
    return f"{getattr(uploaded_file, 'name', '')}:{len(uploaded_file.getvalue())}"


def empty_reading(source_image, status):
    return {
        "schema_version": "1.0",
        "source_image": source_image,
        "status": status,
        "at_bats": [],
    }


def set_new_image_source(image_path):
    source_image = str(image_path.relative_to(PROJECT_ROOT))
    provisional = empty_reading(source_image, "provisional")
    corrected = empty_reading(source_image, "corrected")
    save_json(PROVISIONAL_FILE, provisional)
    save_json(CORRECTED_FILE, corrected)
    reset_editor_state(provisional)


def render_paste_image_input():
    return paste_image_component(key="paste-image-component")


def build_codex_reading_request(image_path):
    prompt_context = build_markdown()
    PROMPT_CONTEXT_FILE.write_text(prompt_context, encoding="utf-8")
    image_text = "未選択"
    if image_path:
        image_text = str(image_path.resolve())

    return f"""# Codexへのスコアブック仮読み取り依頼

以下の画像を読解し、`outputs/provisional_reading.json` に保存できる仮読み取りJSONを作成してください。

画像ファイル:

```text
{image_text}
```

## 目的

この作業の目的は、チーム成績DBを完成させることではありません。スコアブック画像を仮読み取りし、人間がStreamlit画面で修正できる形のJSONを作ることです。

## 出力先

`outputs/provisional_reading.json`

## 出力形式

```json
{{
  "schema_version": "1.0",
  "source_image": "inputs/images/画像ファイル名",
  "status": "provisional",
  "at_bats": [
    {{
      "id": "inning1-batter1",
      "inning": 1,
      "batter_number": 1,
      "symbols": ["読み取った記号や投球内容"],
      "interpretations": ["記号の解釈"],
      "cumulative_pitch_count": 0,
      "batting_result": "打撃結果",
      "out_count": "",
      "runner_events": [],
      "notes": "曖昧な点や根拠"
    }}
  ]
}}
```

## 読解時の注意

- 断定できない箇所は `notes` に推測として明示してください。
- 小さい数字は相手投手の累計投球数として扱ってください。
- 「’」は独立した投球ではなく、同時イベントの印として扱ってください。
- `B` や `SK` は最後の投球を兼ねるため、投球数を二重計上しないでください。
- 画像内に読めないマスがある場合も、分かる打席だけでJSONを作ってください。

## 最新ルールブック

{prompt_context}
"""


def next_example_id(inning, batter_number, existing_examples):
    base_id = f"inning{inning}-batter{batter_number}"
    existing_ids = {example.get("id") for example in existing_examples}
    if base_id not in existing_ids:
        return base_id
    index = 2
    while f"{base_id}-{index}" in existing_ids:
        index += 1
    return f"{base_id}-{index}"


def normalize_at_bat(at_bat, index):
    normalized = deepcopy(at_bat)
    normalized.setdefault("id", f"at-bat-{index + 1}")
    normalized.setdefault("inning", 1)
    normalized.setdefault("batter_number", index + 1)
    normalized.setdefault("symbols", [])
    normalized.setdefault("interpretations", [])
    normalized.setdefault("cumulative_pitch_count", None)
    normalized.setdefault("batting_result", "")
    normalized.setdefault("out_count", "")
    normalized.setdefault("runner_events", [])
    normalized.setdefault("notes", "")
    return normalized


def reading_signature(reading_data):
    return json.dumps(reading_data.get("at_bats", []), ensure_ascii=False, sort_keys=True)


def reset_editor_state(source_data, prefer_corrected=False):
    if prefer_corrected:
        existing_corrected = load_json(CORRECTED_FILE, {})
        source_at_bats = existing_corrected.get("at_bats") or source_data.get("at_bats", [])
    else:
        source_at_bats = source_data.get("at_bats", [])
    st.session_state.edited_at_bats = [
        normalize_at_bat(at_bat, index) for index, at_bat in enumerate(source_at_bats)
    ]
    st.session_state.editor_source_signature = reading_signature(source_data)
    st.session_state.editor_generation = st.session_state.get("editor_generation", 0) + 1


def build_corrected_reading(source_data, edited_at_bats):
    corrected = deepcopy(source_data)
    corrected["status"] = "corrected"
    corrected["at_bats"] = edited_at_bats
    corrected.setdefault("correction_notes", [])
    return corrected


def load_sample_game():
    provisional = load_json(SAMPLE_PROVISIONAL_FILE, {})
    corrected = load_json(SAMPLE_CORRECTED_FILE, {})
    save_json(PROVISIONAL_FILE, provisional)
    save_json(CORRECTED_FILE, corrected)
    reset_editor_state(provisional, prefer_corrected=True)


def add_reading_example(at_bat):
    data = load_json(READING_EXAMPLES_FILE, {"schema_version": "1.0", "examples": []})
    examples = data.setdefault("examples", [])
    example = {
        "id": next_example_id(at_bat["inning"], at_bat["batter_number"], examples),
        "inning": at_bat["inning"],
        "batter_number": at_bat["batter_number"],
        "symbols": at_bat.get("symbols", []),
        "interpretations": at_bat.get("interpretations", []),
        "batting_result": at_bat.get("batting_result", ""),
        "notes": at_bat.get("notes", ""),
    }
    if at_bat.get("cumulative_pitch_count") is not None:
        example["cumulative_pitch_count"] = at_bat["cumulative_pitch_count"]
    if at_bat.get("out_count"):
        example["out_count"] = at_bat["out_count"]
    examples.append(example)
    save_json(READING_EXAMPLES_FILE, data)
    return example["id"]


def add_all_current_examples(at_bats):
    added = []
    for at_bat in at_bats:
        added.append(add_reading_example(at_bat))
    return added


def add_symbol_rule(symbol, reading, category, description, aliases):
    data = load_json(SYMBOL_RULES_FILE, {"schema_version": "1.0", "rules": []})
    rules = data.setdefault("rules", [])
    tokens = {symbol, *aliases}
    duplicates = [
        rule
        for rule in rules
        if symbol == rule.get("symbol") or tokens.intersection({rule.get("symbol", ""), *rule.get("aliases", [])})
    ]
    if duplicates:
        duplicate_text = "、".join(f"{rule.get('symbol')}={rule.get('reading')}" for rule in duplicates)
        return False, f"既存ルールと重複している可能性があります: {duplicate_text}"

    rule_id = f"symbol-{slugify(symbol, 'symbol')}"
    existing_ids = {rule.get("id") for rule in rules}
    if rule_id in existing_ids:
        index = 2
        while f"{rule_id}-{index}" in existing_ids:
            index += 1
        rule_id = f"{rule_id}-{index}"

    rules.append(
        {
            "id": rule_id,
            "symbol": symbol,
            "aliases": aliases,
            "category": category or "未分類",
            "reading": reading,
            "description": description or reading,
        }
    )
    save_json(SYMBOL_RULES_FILE, data)
    return True, f"追加しました: {rule_id}"


def add_compound_rule(name, conditions, interpretation, priority):
    data = load_json(COMPOUND_RULES_FILE, {"schema_version": "1.0", "rules": []})
    rules = data.setdefault("rules", [])
    duplicates = [
        rule
        for rule in rules
        if rule.get("name") == name or rule.get("conditions") == conditions
    ]
    if duplicates:
        duplicate_text = "、".join(rule.get("name", "") for rule in duplicates)
        return False, f"既存の複合ルールと重複している可能性があります: {duplicate_text}"

    rule_id = f"compound-{slugify(name, 'compound')}"
    existing_ids = {rule.get("id") for rule in rules}
    if rule_id in existing_ids:
        index = 2
        while f"{rule_id}-{index}" in existing_ids:
            index += 1
        rule_id = f"{rule_id}-{index}"

    rules.append(
        {
            "id": rule_id,
            "name": name,
            "conditions": conditions,
            "interpretation": interpretation,
            "priority": priority,
        }
    )
    data["rules"] = sorted(rules, key=lambda rule: rule.get("priority", 0), reverse=True)
    save_json(COMPOUND_RULES_FILE, data)
    return True, f"追加しました: {rule_id}"


def get_image_files():
    if not INPUT_IMAGE_DIR.exists():
        return []
    return sorted(path for path in INPUT_IMAGE_DIR.iterdir() if path.suffix.lower() in IMAGE_EXTENSIONS)


def image_data_uri(image_path):
    mime_type, _ = mimetypes.guess_type(image_path.name)
    if not mime_type:
        mime_type = "image/png"
    encoded = base64.b64encode(image_path.read_bytes()).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def render_image_preview(image_path):
    data_uri = image_data_uri(image_path)
    escaped_name = html.escape(image_path.name)
    components.html(
        f"""
        <div style="
          width: 100%;
          min-height: 180px;
          display: flex;
          align-items: center;
          justify-content: center;
          background: #fafafa;
          border: 1px solid rgba(49, 51, 63, 0.12);
          border-radius: 8px;
          padding: 8px;
          box-sizing: border-box;
        ">
          <img
            src="{data_uri}"
            alt="{escaped_name}"
            title="{escaped_name}"
            style="
              display: block;
              max-width: 100%;
              max-height: {MAX_IMAGE_PREVIEW_HEIGHT}px;
              width: auto;
              height: auto;
              object-fit: contain;
            "
          />
        </div>
        """,
        height=MAX_IMAGE_PREVIEW_HEIGHT + 24,
        scrolling=False,
    )


def ensure_state():
    source_data = load_json(
        PROVISIONAL_FILE,
        {"schema_version": "1.0", "source_image": "", "status": "provisional", "at_bats": []},
    )
    signature = reading_signature(source_data)
    if (
        "edited_at_bats" not in st.session_state
        or st.session_state.get("editor_source_signature") != signature
    ):
        reset_editor_state(source_data)
    return source_data


def render_image_panel(source_data):
    st.subheader("画像")
    uploaded_image = st.file_uploader(
        "画像をアップロード",
        type=IMAGE_UPLOAD_TYPES,
        help="Finderから選ぶ、またはこの枠へドラッグ&ドロップできます。",
    )
    if uploaded_image is not None:
        signature = uploaded_file_signature(uploaded_image)
        if signature != st.session_state.get("last_uploaded_image_signature"):
            saved_image = save_uploaded_image(uploaded_image)
            st.session_state.last_uploaded_image_signature = signature
            set_new_image_source(saved_image)
            st.success(f"画像を保存しました: {saved_image.name}。仮読み取りJSONは空にしました。")
            st.rerun()

    pasted_payload = render_paste_image_input()
    if pasted_payload:
        signature = pasted_payload.get("signature")
        if signature != st.session_state.get("last_pasted_image_signature"):
            try:
                saved_image = save_pasted_image(pasted_payload)
            except (ValueError, binascii.Error) as error:
                st.error(f"貼り付け画像を保存できませんでした: {error}")
            else:
                st.session_state.last_pasted_image_signature = signature
                set_new_image_source(saved_image)
                st.success(f"貼り付け画像を保存しました: {saved_image.name}。仮読み取りJSONは空にしました。")
                st.rerun()

    image_files = get_image_files()
    source_image = source_data.get("source_image", "")
    default_index = 0
    for index, image_file in enumerate(image_files):
        if source_image and image_file.name in source_image:
            default_index = index
            break

    if not image_files:
        st.info("inputs/images/ に画像を置くと、ここに表示されます。")
        return None

    if not source_data.get("at_bats"):
        st.info("画像の貼り付け・アップロードだけでは読解結果は生成されません。AIの仮読み取りJSONを outputs/provisional_reading.json に入れてから再読み込みしてください。")

    selected_image = st.selectbox(
        "表示する画像",
        image_files,
        index=default_index,
        format_func=lambda path: path.name,
    )
    render_image_preview(selected_image)
    return selected_image


def compare_readings(provisional, corrected):
    rows = []
    provisional_by_id = {at_bat.get("id"): at_bat for at_bat in provisional.get("at_bats", [])}
    for corrected_at_bat in corrected.get("at_bats", []):
        at_bat_id = corrected_at_bat.get("id")
        provisional_at_bat = provisional_by_id.get(at_bat_id, {})
        for field, label in [
            ("symbols", "投球内容"),
            ("interpretations", "解釈"),
            ("cumulative_pitch_count", "累計投球数"),
            ("batting_result", "打撃結果"),
            ("out_count", "アウトカウント"),
            ("runner_events", "走者イベント"),
            ("notes", "備考"),
        ]:
            before = provisional_at_bat.get(field, "")
            after = corrected_at_bat.get(field, "")
            if before != after:
                rows.append(
                    {
                        "打席": f"{corrected_at_bat.get('inning')}回{corrected_at_bat.get('batter_number')}人目",
                        "項目": label,
                        "修正前": format_cell_value(before),
                        "修正後": format_cell_value(after),
                    }
                )
    return rows


def render_comparison(source_data):
    corrected = load_json(CORRECTED_FILE, {})
    if not corrected.get("at_bats"):
        st.info("corrected_reading.json に修正結果を保存すると、比較を表示できます。")
        return

    rows = compare_readings(source_data, corrected)
    if not rows:
        st.success("修正前後の差分はありません。")
        return
    st.dataframe(rows, use_container_width=True, hide_index=True)


def run_schema_validation():
    errors = []
    for data_path, schema_path in validate_rules.VALIDATION_TARGETS:
        file_errors = validate_rules.validate_file(data_path, schema_path)
        errors.extend(f"{data_path}: {error}" for error in file_errors)
    return errors


def render_operational_actions():
    action_cols = st.columns(4)
    with action_cols[0]:
        if st.button("サンプルデータを読み込む"):
            load_sample_game()
            st.success("sample_game_001 を outputs/ に読み込みました。")
            st.rerun()
    with action_cols[1]:
        if st.button("ルールブックを再生成"):
            PROMPT_CONTEXT_FILE.write_text(build_markdown(), encoding="utf-8")
            st.success("outputs/prompt_context.md を再生成しました。")
    with action_cols[2]:
        if st.button("全データを検証"):
            errors = run_schema_validation()
            errors.extend(operational_checks.collect_all_validation_errors(PROJECT_ROOT))
            if errors:
                st.error("検証エラーがあります。")
                for error in errors:
                    st.write(f"- {error}")
            else:
                st.success("全データの検証に成功しました。")
    with action_cols[3]:
        if st.button("全打席を事例として追加"):
            if not st.session_state.get("edited_at_bats"):
                st.warning("追加する修正済み打席がありません。")
            else:
                added = add_all_current_examples(st.session_state.edited_at_bats)
                st.success(f"{len(added)}件を reading_examples.json に追加しました。")


def render_codex_request_actions(selected_image):
    st.subheader("Codex手動読解")
    st.caption("APIを使わず、選択中の画像と最新ルールブックをCodexに渡すための依頼Markdownを生成します。")

    if selected_image:
        st.code(str(selected_image.resolve()), language="text")
    else:
        st.warning("先に画像をアップロード、貼り付け、または選択してください。")

    if st.button("Codex読解依頼Markdownを生成", disabled=selected_image is None):
        request_markdown = build_codex_reading_request(selected_image)
        CODEX_READING_REQUEST_FILE.write_text(request_markdown, encoding="utf-8")
        st.success(f"{CODEX_READING_REQUEST_FILE.relative_to(PROJECT_ROOT)} を生成しました。")

    if CODEX_READING_REQUEST_FILE.exists():
        with st.expander("生成済み依頼Markdownを表示", expanded=False):
            st.code(CODEX_READING_REQUEST_FILE.read_text(encoding="utf-8"), language="markdown")


def render_at_bat_editor(at_bat, index):
    generation = st.session_state.get("editor_generation", 0)
    title = f"{at_bat.get('inning', '')}回 {at_bat.get('batter_number', '')}人目"
    with st.expander(title, expanded=index == 0):
        left, right = st.columns([2, 1])
        with left:
            inning = st.number_input(
                "イニング",
                min_value=1,
                value=int(at_bat.get("inning") or 1),
                key=f"inning-{generation}-{index}",
            )
            batter_number = st.number_input(
                "打者番号",
                min_value=1,
                value=int(at_bat.get("batter_number") or index + 1),
                key=f"batter-{generation}-{index}",
            )
            symbols_text = st.text_area(
                "投球内容・記号",
                value=join_list(at_bat.get("symbols", [])),
                help="1行に1つずつ入力します。",
                key=f"symbols-{generation}-{index}",
            )
            interpretations_text = st.text_area(
                "解釈",
                value=join_list(at_bat.get("interpretations", [])),
                help="1行に1つずつ入力します。",
                key=f"interpretations-{generation}-{index}",
            )
            batting_result = st.text_input(
                "打撃結果",
                value=at_bat.get("batting_result", ""),
                key=f"result-{generation}-{index}",
            )
        with right:
            pitch_count_value = at_bat.get("cumulative_pitch_count")
            pitch_count = st.number_input(
                "累計投球数",
                min_value=0,
                value=int(pitch_count_value) if pitch_count_value is not None else 0,
                key=f"pitch-count-{generation}-{index}",
            )
            has_pitch_count = st.checkbox(
                "累計投球数を保存",
                value=pitch_count_value is not None,
                key=f"has-pitch-count-{generation}-{index}",
            )
            out_count = st.text_input(
                "アウトカウント",
                value=at_bat.get("out_count", ""),
                key=f"out-{generation}-{index}",
            )
            runner_events_text = st.text_area(
                "走者イベント",
                value=join_list(at_bat.get("runner_events", [])),
                help="例: 三塁走者ホームイン",
                key=f"runner-events-{generation}-{index}",
            )
            notes = st.text_area("備考", value=at_bat.get("notes", ""), key=f"notes-{generation}-{index}")

        updated = deepcopy(at_bat)
        updated.update(
            {
                "inning": int(inning),
                "batter_number": int(batter_number),
                "symbols": split_lines(symbols_text),
                "interpretations": split_lines(interpretations_text),
                "cumulative_pitch_count": int(pitch_count) if has_pitch_count else None,
                "batting_result": batting_result.strip(),
                "out_count": out_count.strip(),
                "runner_events": split_lines(runner_events_text),
                "notes": notes.strip(),
            }
        )

        button_cols = st.columns(3)
        with button_cols[0]:
            if st.button("読み取り事例として追加", key=f"example-{generation}-{index}"):
                example_id = add_reading_example(updated)
                st.success(f"reading_examples.json に追加しました: {example_id}")
        with button_cols[1]:
            st.caption("単独記号は下のフォームから追加")
        with button_cols[2]:
            st.caption("複合ルールは下のフォームから追加")

    return updated


def render_rule_forms():
    st.subheader("ルール辞書へ反映")
    symbol_tab, compound_tab = st.tabs(["新しい記号ルール", "複合ルール"])

    with symbol_tab:
        with st.form("symbol-rule-form"):
            symbol = st.text_input("記号")
            reading = st.text_input("読み")
            category = st.text_input("分類", value="未分類")
            aliases_text = st.text_input("別表記", help="カンマ区切りで入力します。")
            description = st.text_area("説明")
            submitted = st.form_submit_button("新しい記号ルールとして追加")
        if submitted:
            if not symbol.strip() or not reading.strip():
                st.error("記号と読みは必須です。")
            else:
                ok, message = add_symbol_rule(
                    symbol.strip(),
                    reading.strip(),
                    category.strip(),
                    description.strip(),
                    split_csv(aliases_text),
                )
                if ok:
                    st.success(message)
                else:
                    st.warning(message)

    with compound_tab:
        with st.form("compound-rule-form"):
            name = st.text_input("ルール名")
            conditions_text = st.text_area("条件", help="1行に1条件ずつ入力します。")
            interpretation = st.text_area("解釈")
            priority = st.number_input("優先度", min_value=0, max_value=100, value=80)
            submitted = st.form_submit_button("複合ルールとして追加")
        if submitted:
            conditions = split_lines(conditions_text)
            if not name.strip() or not conditions or not interpretation.strip():
                st.error("ルール名、条件、解釈は必須です。")
            else:
                ok, message = add_compound_rule(name.strip(), conditions, interpretation.strip(), int(priority))
                if ok:
                    st.success(message)
                else:
                    st.warning(message)


def main():
    st.title("Scorebook Reader")
    st.caption("AIの仮読み取りJSONを人間が確認・修正し、読み取り事例とルール辞書に反映するためのローカル画面です。")

    render_operational_actions()
    st.divider()

    source_data = ensure_state()
    top_left, top_right = st.columns([1, 1])
    with top_left:
        selected_image = render_image_panel(source_data)
    with top_right:
        st.subheader("仮読み取りJSON")
        st.json(source_data, expanded=False)
        if st.button("provisional_reading.json を再読み込み"):
            reset_editor_state(source_data)
            st.rerun()

    render_codex_request_actions(selected_image)

    st.subheader("修正前後を比較")
    render_comparison(source_data)

    st.divider()
    st.subheader("打席ごとの確認・修正")

    if not st.session_state.edited_at_bats:
        st.info("outputs/provisional_reading.json に at_bats を追加すると、修正フォームが表示されます。")
        if st.button("サンプル仮読み取りを読み込む"):
            sample = load_json(SAMPLE_PROVISIONAL_FILE, {})
            reset_editor_state(sample)
            st.rerun()
    else:
        updated_at_bats = []
        for index, at_bat in enumerate(st.session_state.edited_at_bats):
            updated_at_bats.append(render_at_bat_editor(at_bat, index))
        st.session_state.edited_at_bats = updated_at_bats

        if st.button("修正結果を corrected_reading.json に保存", type="primary"):
            corrected = build_corrected_reading(source_data, st.session_state.edited_at_bats)
            save_json(CORRECTED_FILE, corrected)
            st.success("outputs/corrected_reading.json に保存しました。")

    st.divider()
    render_rule_forms()


if __name__ == "__main__":
    main()
