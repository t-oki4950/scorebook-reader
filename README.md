# scorebook-reader

草野球・軟式野球のスコアブック画像をAIが仮読み取りし、人間が修正し、その修正内容を「読解ルール」として蓄積するためのローカル最小構成プロジェクトです。

このプロジェクトの目的は、チーム成績DBや打席成績データをいきなり完成させることではありません。目的は、スコアブック画像に書かれた記号、位置、複合的な文脈、読み取り事例を少しずつ育て、次回以降の画像読解に再利用できる知識ベースを作ることです。

## ディレクトリ構成

```text
scorebook-reader/
├─ README.md
├─ rules/
│  ├─ symbol_dictionary.json
│  ├─ position_rules.json
│  ├─ compound_rules.json
│  └─ scorer_style_notes.md
├─ examples/
│  ├─ reading_examples.json
│  └─ sample_game_001/
│     ├─ provisional_reading.json
│     ├─ corrected_reading.json
│     ├─ expected_prompt_context.md
│     └─ README.md
├─ inputs/
│  └─ images/
├─ outputs/
│  ├─ provisional_reading.json
│  ├─ corrected_reading.json
│  ├─ sample_provisional_reading.json
│  ├─ sample_corrected_reading.json
│  └─ prompt_context.md
├─ docs/
│  ├─ workflow.md
│  └─ how_to_add_new_rule.md
├─ prompts/
│  └─ scorebook_reading_prompt.md
├─ schemas/
│  ├─ symbol_rule.schema.json
│  ├─ position_rule.schema.json
│  ├─ compound_rule.schema.json
│  └─ reading_example.schema.json
└─ scripts/
   ├─ add_symbol_rule.py
   ├─ add_position_rule.py
   ├─ add_compound_rule.py
   ├─ add_reading_example.py
   ├─ build_prompt_context.py
   ├─ validate_rules.py
   └─ operational_checks.py
```

## 実運用テスト

`examples/sample_game_001/` に、1回表7人分の仮読み取りと修正済みデータを用意しています。画像認識AIとのAPI接続は使わず、固定のサンプルJSONで一巡確認します。

Streamlit画面で確認する場合:

1. `.venv/bin/streamlit run app.py` を起動する。
2. `http://127.0.0.1:8501` を開く。
3. 「サンプルデータを読み込む」を押す。
4. 画像、仮読み取りJSON、修正フォーム、修正前後比較を確認する。
5. 「修正結果を corrected_reading.json に保存」を押す。
6. 必要に応じて「全打席を事例として追加」を押す。
7. 必要に応じて「新しい記号ルール」または「複合ルール」から辞書へ登録する。
8. 「ルールブックを再生成」を押す。
9. 「全データを検証」を押す。

コマンドで確認する場合:

```bash
python3 scripts/validate_rules.py
python3 scripts/operational_checks.py --all
python3 scripts/build_prompt_context.py --output outputs/prompt_context.md
pytest
```

仮想環境を使っている場合:

```bash
.venv/bin/python scripts/validate_rules.py
.venv/bin/python scripts/operational_checks.py --all
.venv/bin/python scripts/build_prompt_context.py --output outputs/prompt_context.md
.venv/bin/pytest
```

## 人間修正をルール化する流れ

詳しい手順は `docs/workflow.md` にまとめています。

1. スコアブック画像を `inputs/images/` に置く。
2. AIの仮読み取り結果を `outputs/provisional_reading.json` に保存する。
3. 人間が修正した結果を `outputs/corrected_reading.json` に保存する。
4. `scripts/add_reading_example.py` で修正済み事例を `examples/reading_examples.json` に追加する。
5. 必要なら単独記号を `rules/symbol_dictionary.json`、複合判断を `rules/compound_rules.json` に追加する。
6. `scripts/build_prompt_context.py` で次回AIに渡すルールブックMarkdownを生成する。

仮読み取りと修正結果の書き方は、次のサンプルを参照してください。

- `outputs/sample_provisional_reading.json`
- `outputs/sample_corrected_reading.json`

## Macで確認・修正画面を起動する

Streamlitで、画像、AIの仮読み取りJSON、修正フォーム、事例追加、ルール追加を扱えます。

初回だけ依存パッケージを入れます。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

起動します。

```bash
.venv/bin/streamlit run app.py
```

ブラウザで `http://127.0.0.1:8501` を開きます。

画像は次の方法で `inputs/images/` に保存できます。

- 画面の「画像をアップロード」から選ぶ。
- 「画像をアップロード」へドラッグ&ドロップする。
- 「クリップボードから画像を貼り付け」の枠をクリックして Cmd+V で貼り付ける。

画像を追加すると、古い仮読み取り・修正結果は空になります。画像認識AIはまだ接続していないため、読解結果を表示するには `outputs/provisional_reading.json` にAIの仮読み取りJSONを入れてから、画面の再読み込みボタンを押します。

API従量課金を避けたい場合は、画面の「Codex読解依頼Markdownを生成」を押します。`outputs/codex_reading_request.md` に、選択中の画像パス、出力してほしいJSON形式、最新ルールブックがまとまります。そのMarkdownをCodexに渡して仮読み取りJSONを作成し、`outputs/provisional_reading.json` に保存してから画面で再読み込みします。

## 新しい記号を追加する

単独記号の読み方は `rules/symbol_dictionary.json` に保存します。追加は次のように行います。

```bash
python3 scripts/add_symbol_rule.py \
  --symbol "H" \
  --reading "ヒット" \
  --category "打撃結果" \
  --description "打者が安打で出塁したことを示す"
```

既存の記号や別表記と重複する場合は警告が出ます。確認したうえで追加したい場合は `--allow-duplicate` を付けます。

## 位置ルールを追加する

マスのどこに書かれているかで意味が変わるルールは `rules/position_rules.json` に保存します。

```bash
python3 scripts/add_position_rule.py \
  --cell-region "正方形の右下付近" \
  --meaning "1塁到達" \
  --description "右下の進塁線や記号は一塁到達として読む"
```

## 複合ルールを追加する

複数の記号、位置、走者状況、アウトカウントを組み合わせるルールは `rules/compound_rules.json` に保存します。

```bash
python3 scripts/add_compound_rule.py \
  --name "送りバント成功" \
  --condition "◇がある" \
  --condition "打者がアウトになっている" \
  --condition "走者が進塁している" \
  --interpretation "送りバント成功" \
  --priority 80
```

## 人間が修正した読解例を追加する

AIの仮読み取りを人間が修正したら、次回の参考例として `examples/reading_examples.json` に追加します。

`outputs/corrected_reading.json` の打席IDから追加する場合:

```bash
python3 scripts/add_reading_example.py \
  --from-corrected outputs/corrected_reading.json \
  --at-bat-id sample-inning1-batter5
```

手入力で追加する場合:

```bash
python3 scripts/add_reading_example.py \
  --inning 2 \
  --batter-number 3 \
  --symbols "ー,✗,△,B,小さい35" \
  --interpretations "ボール,見逃しストライク,ファール,フォアボール" \
  --cumulative-pitch-count 35 \
  --batting-result "フォアボール" \
  --notes "投球数の小さい数字が薄い"
```

## 次回AIに読ませるプロンプトを作る

蓄積したルールと事例をAIに渡すためのMarkdownコンテキストは、次のコマンドで生成します。

```bash
python3 scripts/build_prompt_context.py --output outputs/prompt_context.md
```

次回の画像読解では、`prompts/scorebook_reading_prompt.md` の本文に、生成された `outputs/prompt_context.md` を添付します。AIは単独記号、位置ルール、複合ルール、過去の読み取り事例を参照して仮読み取りを行います。

## ルールを検証する

JSONファイルがスキーマに合っているか確認します。

```bash
python3 scripts/validate_rules.py
```

## 将来のWebアプリ化方針

まずはJSON、Markdown、CSVに近い扱いやすい構造で読解ルールを育てます。画像認識AIとの接続やWebアプリ化は後回しにし、ルールの形が安定してから次の拡張を行います。

- Streamlitで、画像、AI仮読み取り、人間修正、ルール追加を1画面で扱う。
- FastAPIで、画像読解リクエスト、ルール検索、修正事例登録のAPIを提供する。
- 将来的には、修正差分から記号ルール、位置ルール、複合ルールの候補を自動提案する。
