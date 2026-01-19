# 検索拡張（RAG）機能 仕様書

本ドキュメントは、将棋解説文生成における検索拡張（RAG: Retrieval-Augmented Generation）の仕様をまとめたものです。対象は OpenAI を用いた解説生成パイプラインです。

---

## 1. 目的

- 既存の教師データ（局面特徴＋解説文）から類似局面を検索し、解説生成の質と安定性を向上させる。
- 生成コストを抑えつつ、説明の一貫性・網羅性を改善する。

---

## 2. 入力データ

- 形式: JSONL
- 各行の必須項目
  - `sfen` : 局面のSFEN
  - `features_text` : 局面特徴テキスト（解説文を含む場合あり）
  - `commentary` : 教師解説文
  - `source_file` : 出典（任意）

---

## 3. ベクトル化対象と短縮方針

### 3.1 教師解説の除去
- `features_text` 内の `【解説文】` 以降は埋め込み前に除去する。

### 3.2 盤面の短縮方針
- `【盤面】` 以降は「1マス要約行（例: `4八: 先手金`）」のみを抽出。
- これにより盤面部分は最大81行に抑えられる。

### 3.3 文字数上限
- `rag-max-feature-chars` で上限を設定。
- デフォルトは 2000 文字。

---

## 4. インデックス構築

### 4.1 出力ファイル
- `<base>.npz` : 正規化済み埋め込みベクトル
- `<base>.meta.jsonl` : 対応するメタ情報（SFEN、特徴、解説）
- `<base>.info.json` : 作成時情報（件数、次元数、モデル名など）

### 4.2 正規化
- 埋め込みは L2 正規化し、内積＝コサイン類似度で検索。

### 4.3 進捗表示
- `--rag-progress-every` で進捗表示の間隔（件数）を制御。
- 進捗表示には「処理済み件数/総件数」「経過時間」「残り時間推定」を含む。

---

## 5. 検索仕様

- クエリは「入力局面の features_text（短縮済み）」を埋め込み。
- 近傍探索は全ベクトルに対して内積で類似度算出。
- 上位 `top_k` 件を取得。

---

## 6. プロンプト組み込み

- 取得した参考例は「局面特徴」と「解説文」を対で挿入。
- `--rag-no-compact` 指定時は `features_text_full` を使用し、フル表記で例示。

---

## 6.1 解説文生成時のRAG利用フロー

解説文生成（`--sfen` または `--input/--output`）時は以下の手順でRAGを利用する。

1. **入力局面の特徴生成**
  - SFENから`features_text`を生成。
  - 生成後、`features_text`は短縮ルールに従いコンパクト化される。

2. **クエリ埋め込みの作成**
  - 短縮済み`features_text`を埋め込みAPIに投入し、クエリベクトルを生成する。
  - ベクトルはL2正規化される。

3. **類似局面検索**
  - `idx_full`に保存されている埋め込みと内積を計算し、上位`top_k`件を取得。
  - `--rag-top-k`の値が検索件数になる。

4. **プロンプト組み立て**
  - 取得した参考例（局面特徴 + 解説文）をプロンプトに挿入。
  - その後に対象局面の`features_text`を付与して解説生成を要求。

5. **解説文生成**
  - OpenAIモデルにより最終的な解説文を生成。

### 実装箇所

- 入力局面の特徴生成: [src/training/generate_commentary_openai.py](src/training/generate_commentary_openai.py)
  - `extract_features_text_from_sfen()`
- 短縮（コンパクト化）: [src/training/generate_commentary_openai.py](src/training/generate_commentary_openai.py)
  - `_compact_features_text()`
- クエリ埋め込み生成: [src/training/generate_commentary_openai.py](src/training/generate_commentary_openai.py)
  - `_embed_texts()`
- 類似局面検索: [src/training/generate_commentary_openai.py](src/training/generate_commentary_openai.py)
  - `retrieve_rag_examples()`
- プロンプト組み立て: [src/training/generate_commentary_openai.py](src/training/generate_commentary_openai.py)
  - `make_prompt()`

---

## 7. 既定のインデックス

- `--rag-index` を省略した場合は **`data/rag/idx_full`** を使用。
- これにより約30,000件（`training_data_filtered.jsonl` 全件）を検索対象とする。

---

## 8. 例外・失敗時の挙動

- インデックス構築に失敗した場合は例外終了。
- API失敗時はバッチ単位で止まるため `--resume` で再開可能。
- `--rag-index` または `--rag-examples` が未指定の場合、RAGは無効。

---

## 9. パフォーマンスと制約

- 埋め込み API の入力上限（トークン制限）を超える場合はエラー。
- そのため、全文を1本で埋め込むのではなく短縮が必須。
- 高精度な埋め込みが必要な場合は `text-embedding-3-large` 等に切替可能だが、入力上限は残る。

---

## 10. 推奨運用

- インデックスは一度作成すれば再利用可能。
- 教師データ更新時のみ再構築。
- `idx_full` を正規の既定インデックスとして運用し、`idx_train100` の利用は推奨しない。

---

## 11. 実行例（概要）

- インデックス作成のみ: `--build-rag-index-only`
- 進捗表示を細かく: `--rag-progress-every 500`
- 再開: `--resume`

---

## 12. 今後の拡張案

- チャンク化による全文埋め込み
- 盤面要約のより高度な正規化（手番・持ち駒の構造化）
- 類似度閾値による動的 `top_k` 制御

