# Shogi Commentary Generator (将棋解説文生成システム)
将棋の局面を解析し、プロ棋士レベルの解説文を自動生成するシステムです。
## 機能
- **局面特徴の抽出**: 評価値、駒得、玉安全度、囲い、戦法、駒の働きなど
- **シミュレーション**: 複数の変化手順を探索し、末端局面の評価を取得
- **RAG (Retrieval-Augmented Generation)**: 類似局面の参考例をプロンプトに含める
- **解説文生成**: OpenAI GPTを使用して自然な日本語の解説文を生成
## 必要条件
- Python 3.11+
- OpenAI API キー
- 将棋エンジン（YaneuraOu）※別途配布
- Maia2 ONNXモデル ※別途配布
- 訓練データ（棋譜コメント）※別途配布
## セットアップ
### 1. 依存関係のインストール
```bash
python -m venv .venv
.venv\Scripts\Activate.ps1  # Windows
# または
source .venv/bin/activate   # Linux/Mac
pip install -r requirements.txt
```
### 2. 環境変数の設定
`.env`ファイルを作成:
```
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4.1-2025-04-14
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```
### 3. エンジン・モデル・データの配置（別途配布）
以下のファイルは別途配布されます。指定のパスに配置してください。
#### やねうら王エンジン
| ファイル | 配置先パス | 用途 |
|---------|-----------|------|
| `YaneuraOu_NNUE_*.exe` | `engine/yaneuraou/` | やねうら王本体 |
| `nn.bin` または評価関数 | `engine/yaneuraou/eval/` | 評価関数 |
**パス変更方法**: `src/simulation/engine_wrapper.py` の `DEFAULT_ENGINE_PATH` を編集
```python
# src/simulation/engine_wrapper.py (L20-24)
DEFAULT_ENGINE_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "engine", "yaneuraou",
    "YaneuraOu_NNUE_halfkp_256x2_32_32-V900Git_ZEN2.exe"  # ← ここを変更
)
```
または実行時に`EngineConfig`で指定:
```python
from src.simulation.engine_wrapper import EngineConfig, YaneuraouWrapper
config = EngineConfig(path="path/to/your/engine.exe")
wrapper = YaneuraouWrapper(config)
```
---
#### Maia2 ONNXモデル
| ファイル | 配置先パス | 用途 |
|---------|-----------|------|
| `model.onnx` | `models/` | Maia2モデル（人間らしい手を予測） |
**パス変更方法**: `src/simulation/maia2_wrapper.py` の `DEFAULT_MODEL_PATH` を編集
```python
# src/simulation/maia2_wrapper.py (L28-31)
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "models", "model.onnx"  # ← ここを変更
)
```
または実行時に`Maia2Config`で指定:
```python
from src.simulation.maia2_wrapper import Maia2Config, Maia2Wrapper
config = Maia2Config(model_path="path/to/your/model.onnx")
wrapper = Maia2Wrapper(config)
```
---
#### DLShogi 駒働き評価モデル
| ファイル | 配置先パス | 用途 |
|---------|-----------|------|
| `model-dr2_exhi.onnx` | `models/` | 駒の働き評価用 |
**パス変更方法**: `src/features/extractor.py` の `DEFAULT_MODEL_PATH` を編集
```python
# src/features/extractor.py (L42)
DEFAULT_MODEL_PATH = "models/model-dr2_exhi.onnx"  # ← ここを変更
```
---
#### 訓練データ・RAGインデックス
| ファイル | 配置先パス | 用途 |
|---------|-----------|------|
| `training_data_filtered.jsonl` | `data/training/` | スタイル例・RAG用 |
| `idx_full.npz` | `data/rag/` | RAG埋め込みベクトル |
| `idx_full.meta.jsonl` | `data/rag/` | RAGメタデータ |
**パス変更方法**: コマンドラインオプションで指定
```bash
python -m src.training.generate_commentary_openai \
    --rag-index "path/to/rag/index_base" \
    --style-examples-jsonl "path/to/training_data.jsonl"
```
---
## 使用方法
### 単一局面の解説生成
```bash
python -m src.training.generate_commentary_openai --sfen "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
```
### オプション一覧
| オプション | デフォルト値 | 説明 |
|-----------|-------------|------|
| `--sfen` | (必須) | 解説する局面のSFEN |
| `--min-chars` | 500 | 解説文の最小文字数目安 |
| `--max-chars` | 1000 | 解説文の最大文字数目安 |
| `--no-rag` | False | RAGを無効にする |
| `--no-simulation` | False | シミュレーションを無効にする |
| `--rag-index` | `data/rag/idx_full` | RAGインデックスのベースパス |
| `--rag-top-k` | 3 | RAGで取得する参考例の数 |
| `--style-examples-count` | 100 | スタイル例として読み込む解説文の数 |
| `--style-examples-jsonl` | `data/training/training_data_filtered.jsonl` | スタイル例のJSONL |
### シミュレーションなしで実行（エンジン不要）
```bash
python -m src.training.generate_commentary_openai --sfen "..." --no-simulation
```
## テスト
```bash
# エンジン不要のテスト
python -m pytest tests/ --ignore=tests/test_simulation.py --ignore=tests/test_game_simulator.py --ignore=tests/test_maia2_v021.py --ignore=tests/test_wrapper_raw.py
```
## ディレクトリ構成
```
shogiLLM/
├── src/
│   ├── features/       # 局面特徴抽出
│   ├── simulation/     # エンジン連携・シミュレーション
│   ├── training/       # 訓練データ生成・解説文生成
│   └── utils/          # ユーティリティ
├── tests/              # テストコード
├── engine/             # やねうら王（別途配布）
├── models/             # ONNXモデル（別途配布）
├── data/
│   ├── training/       # 訓練データ（別途配布）
│   └── rag/            # RAGインデックス（別途配布）
└── requirements.txt
```
## ライセンス
MIT License