# 新しい読解ルールの追加方法

人間が修正した内容は、すべてをすぐルール化する必要はありません。まず `examples/reading_examples.json` に事例として残し、同じ判断が繰り返し出てきたらルールにします。

## どこに追加するか

単独で意味が決まる記号は `rules/symbol_dictionary.json` に追加します。

例:

- `H`: ヒット
- `DB`: デッドボール
- `K`: 見逃し三振

マス内の位置で意味が決まるものは `rules/position_rules.json` に追加します。

例:

- 正方形の右下付近: 1塁到達
- 正方形の左下付近: 本塁到達

複数の記号、位置、走者状況、アウトカウントを組み合わせて判断するものは `rules/compound_rules.json` に追加します。

例:

- `◇` があり、三塁走者がホームインし、打者が `T.O` ならスクイズ成功
- `WP` が `’` と対応していれば、その投球と同時にワイルドピッチ

記入者の癖や、まだ断定できない傾向は `rules/scorer_style_notes.md` にメモします。

## 単独記号ルールを追加する

```bash
python3 scripts/add_symbol_rule.py \
  --symbol "DB" \
  --reading "デッドボール" \
  --category "打撃結果" \
  --description "死球により打者が出塁したことを示す"
```

別表記がある場合:

```bash
python3 scripts/add_symbol_rule.py \
  --symbol "DB" \
  --aliases "D.B,死球" \
  --reading "デッドボール" \
  --category "打撃結果" \
  --description "死球により打者が出塁したことを示す"
```

## 位置ルールを追加する

```bash
python3 scripts/add_position_rule.py \
  --cell-region "正方形の左下の塗りつぶし" \
  --meaning "本塁到達、得点" \
  --description "左下方向の進塁線と塗りつぶしがある場合は得点として読む"
```

## 複合ルールを追加する

```bash
python3 scripts/add_compound_rule.py \
  --name "ワイルドピッチによる進塁" \
  --condition "WPがある" \
  --condition "WPが「’」と対応している" \
  --condition "走者の進塁線が次の塁まで伸びている" \
  --interpretation "その投球と同時にワイルドピッチが発生し、走者が進塁した。" \
  --priority 90
```

優先度は、他のルールと競合したときにどれを重く見るかの目安です。重要で具体的な複合ルールほど高めにします。

## 読み取り事例を先に追加する

ルール化する前に、修正済みの事例として残します。

```bash
python3 scripts/add_reading_example.py \
  --from-corrected outputs/corrected_reading.json \
  --at-bat-id sample-inning1-batter5
```

手入力でも追加できます。

```bash
python3 scripts/add_reading_example.py \
  --inning 1 \
  --batter-number 5 \
  --symbols "小さい14,◇,3 T.O,Ⅱ" \
  --interpretations "初球スクイズ,三塁走者ホームイン,打者は一塁手にタッチアウト" \
  --cumulative-pitch-count 14 \
  --batting-result "スクイズ成功、打者タッチアウト" \
  --out-count "2アウト目"
```

## 追加後に必ず行うこと

JSONの形を検証します。

```bash
python3 scripts/validate_rules.py
```

次回AIに渡すMarkdownを作り直します。

```bash
python3 scripts/build_prompt_context.py --output outputs/prompt_context.md
```

この `outputs/prompt_context.md` を、次回のスコアブック画像読解プロンプトに添付します。
