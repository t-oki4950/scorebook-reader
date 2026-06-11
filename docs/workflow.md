# 人間修正を読解ルールに育てるワークフロー

このプロジェクトは、スコアブック画像からチーム成績DBを直接作るためのものではありません。AIの仮読み取りを人間が直し、その修正を読み取り事例とルールに変えて、次回以降の読解精度を上げるための土台です。

## 全体の流れ

スコアブック画像をAIに見せる
→ AIが仮読みする
→ 人間が修正する
→ 修正を `reading_examples.json` に追加する
→ 必要なら新規ルールとして登録する
→ 次回、`build_prompt_context.py` で生成したMarkdownをAIのプロンプトに添付する

## 1. スコアブック画像をAIに見せる

画像ファイルは `inputs/images/` に置きます。

```text
inputs/images/
└─ 2026-06-11_game1_inning1.jpg
```

AIに読ませるときは、`prompts/scorebook_reading_prompt.md` と、必要に応じて `outputs/prompt_context.md` を一緒に渡します。初回はルールが少ないため、AIには「仮読み取りでよい」「曖昧な点を残す」ことを明示します。

## 2. AIが仮読みする

AIの仮読み取り結果は `outputs/provisional_reading.json` に保存します。書き方の例は `outputs/sample_provisional_reading.json` を参照してください。

最低限、打席ごとに次の情報を残します。

- `id`: 打席を識別するID
- `inning`: イニング
- `batter_number`: その回の何人目の打者か
- `symbols`: AIが読んだ記号
- `interpretations`: 記号ごとの仮解釈
- `cumulative_pitch_count`: 小さい数字から読んだ累計投球数
- `batting_result`: AIが仮判断した打撃結果
- `uncertain_points`: 人間に確認してほしい点

## 3. 人間が修正する

人間は `outputs/provisional_reading.json` を見ながら、修正結果を `outputs/corrected_reading.json` に保存します。書き方の例は `outputs/sample_corrected_reading.json` を参照してください。

修正するときは、単に結果だけ直すのではなく、「なぜ直したか」も残します。

```json
{
  "at_bat_id": "sample-inning1-batter5",
  "before": "バント、打者タッチアウト",
  "after": "スクイズ成功、打者タッチアウト",
  "reason": "◇、三塁走者ホームイン、3 T.O が同時に成立しているため。"
}
```

この理由が、後で複合ルールを追加するときの材料になります。

## 4. 修正済み事例を reading_examples.json に追加する

修正した打席は、次回AIに見せるための読み取り事例として `examples/reading_examples.json` に追加します。

手入力で追加する場合:

```bash
python3 scripts/add_reading_example.py \
  --inning 1 \
  --batter-number 5 \
  --symbols "小さい14,◇,3 T.O,Ⅱ,マス目中央の●または塗りつぶし" \
  --interpretations "初球スクイズ,三塁走者ホームイン,打者は一塁手にタッチアウト" \
  --cumulative-pitch-count 14 \
  --batting-result "スクイズ成功、打者タッチアウト" \
  --out-count "2アウト目" \
  --notes "人間が三塁走者ホームインを確認"
```

`outputs/corrected_reading.json` の打席IDから追加する場合:

```bash
python3 scripts/add_reading_example.py \
  --from-corrected outputs/corrected_reading.json \
  --at-bat-id sample-inning1-batter5
```

同じIDの事例が既にある場合は警告が出ます。確認済みで追加したい場合は `--allow-duplicate` を付けます。

## 5. 必要なら新規ルールとして登録する

修正内容が一度きりの事例なら、読み取り事例として残すだけで十分です。何度も使えそうな判断なら、ルールとして登録します。

単独記号の例:

```bash
python3 scripts/add_symbol_rule.py \
  --symbol "H" \
  --reading "ヒット" \
  --category "打撃結果" \
  --description "打者が安打で出塁したことを示す"
```

複合判断の例:

```bash
python3 scripts/add_compound_rule.py \
  --name "スクイズ成功、打者タッチアウト" \
  --condition "◇がある" \
  --condition "三塁走者がホームインしている" \
  --condition "打者の結果にT.Oがある" \
  --interpretation "スクイズ成功。三塁走者は得点し、打者はタッチアウト。" \
  --priority 95
```

## 6. 次回AIに渡すルールブックMarkdownを生成する

ルールや事例を追加したら、次回AIに渡すMarkdownを生成します。

```bash
python3 scripts/build_prompt_context.py --output outputs/prompt_context.md
```

次回の読解では、次の2つをAIに渡します。

- `prompts/scorebook_reading_prompt.md`
- `outputs/prompt_context.md`

これにより、AIは過去に人間が直した事例と、そこから作った読解ルールを参照して仮読み取りできます。

## 7. 検証する

JSONを編集した後は、スキーマ検証を実行します。

```bash
python3 scripts/validate_rules.py
```

この検証は、ルールファイルと読み取り事例の形が壊れていないかを確認します。
