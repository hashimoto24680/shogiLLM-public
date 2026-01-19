# Shogi Commentary Generator

将棋の局面を解析し、解説文を自動生成するシステムです。

## 機能

- **局面特徴の抽出**: 評価値、駒得、玉安全度、囲い、戦法、駒の働きなど
- **シミュレーション**: 複数の変化手順を探索し、末端局面の評価を取得
- **RAG (Retrieval-Augmented Generation)**: 類似局面の参考例をプロンプトに含める
- **解説文生成**: OpenAI GPTを使用して自然な日本語の解説文を生成

## 必要条件

- Python 3.11+
- OpenAI API キー
- 将棋エンジン

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

### 3. エンジンの配置

エンジンファイルを`engines/`ディレクトリに配置してください。

```
engines/
├── YaneuraOu/
│   ├── YaneuraOu_NNUE.exe
│   └── suisho5.nnue
└── maia2-shogi-v2/
    ├── maia2-net.pth
    └── ...
```

### 4. 訓練データの配置

データファイルを`data/`ディレクトリに配置してください。

```
data/
├── training/
│   └── training_data_filtered.jsonl
└── rag/
    ├── idx_full.npz
    └── idx_full.meta.jsonl
```

## 使用方法

### 単一局面の解説生成

```bash
python -m src.training.generate_commentary_openai --sfen "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
```

### オプション

```
--sfen         : 解説する局面のSFEN
--min-chars    : 解説文の最小文字数（デフォルト: 500）
--max-chars    : 解説文の最大文字数（デフォルト: 1000）
--no-rag       : RAGを無効にする
--no-simulation: シミュレーションを無効にする
```

## テスト

```bash
python -m pytest tests/ --ignore=tests/test_simulation.py --ignore=tests/test_game_simulator.py --ignore=tests/test_maia2_v021.py --ignore=tests/test_wrapper_raw.py
```

## ライセンス

MIT License
