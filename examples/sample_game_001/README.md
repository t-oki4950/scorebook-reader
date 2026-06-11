# sample_game_001

実運用テスト用のサンプルゲームです。画像認識AIとのAPI接続は行わず、仮読み取りJSONを固定データとして使います。

## ファイル

- `provisional_reading.json`: AIの仮読み取り結果として扱うサンプル
- `corrected_reading.json`: 人間が修正した後の期待データ
- `expected_prompt_context.md`: ルールブックMarkdownに含まれてほしい断片

## 一巡テストの流れ

1. `provisional_reading.json` を `outputs/provisional_reading.json` に読み込む。
2. Streamlit画面で打席ごとに内容を確認・修正する。
3. `outputs/corrected_reading.json` に保存する。
4. 修正済み打席を `examples/reading_examples.json` に追加する。
5. 必要に応じて `IP`、`1H`、同時イベントの投球数扱いなどのルールを辞書へ追加する。
6. `scripts/build_prompt_context.py` で `outputs/prompt_context.md` を再生成する。
7. `scripts/validate_rules.py` と `pytest` を実行する。
