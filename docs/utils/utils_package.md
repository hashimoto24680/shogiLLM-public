# utils パッケージ 関数構成

`src/utils` パッケージは、将棋盤の座標変換、駒の利き計算、棋譜変換など汎用ユーティリティを提供します。

---

## ファイル構成

```
src/utils/
├── __init__.py          # パッケージ定義
├── coordinates.py       # 座標変換
├── attacks.py           # 駒の利き計算
├── KIF_to_usi.py        # KIF↔USI変換
└── dlshogi.py           # dlshogi特徴量→SFEN変換
```

---

## 座標変換（coordinates.py）

**ファイル**: [coordinates.py](file:///c:/Users/hashimoto/shogiLLM/src/utils/coordinates.py)

将棋盤の座標を異なる形式間で変換。

| 関数 | 説明 |
|------|------|
| `japanese_to_index("7七")` | 日本語座標 → インデックス(0-80) |
| `index_to_japanese(40)` | インデックス → 日本語座標 |
| `usi_to_index("5e")` | USI形式 → インデックス |
| `index_to_usi(40)` | インデックス → USI形式 |
| `file_rank_to_index(f, r)` | 筋・段 → インデックス |
| `index_to_file_rank(idx)` | インデックス → (筋, 段) |

```python
>>> from src.utils.coordinates import japanese_to_index, index_to_usi
>>> japanese_to_index("5五")
40
>>> index_to_usi(40)
'5e'
```

📖 座標系の詳細: [coordinate_system.md](file:///c:/Users/hashimoto/shogiLLM/docs/utils/coordinate_system.md)

---

## 駒の利き計算（attacks.py）

**ファイル**: [attacks.py](file:///c:/Users/hashimoto/shogiLLM/src/utils/attacks.py)

指定した駒がどのマスに利いているかを計算。

| 関数 | 説明 |
|------|------|
| `get_piece_attacks(board, sq, type, color)` | 駒の利き先マスリストを取得 |

```python
>>> import cshogi
>>> from src.utils.attacks import get_piece_attacks
>>> board = cshogi.Board()
>>> attacks = get_piece_attacks(board, 60, cshogi.PAWN, cshogi.BLACK)
>>> attacks  # 7七歩の利き先
[51]  # 7六
```

---

## KIF↔USI変換（KIF_to_usi.py）

**ファイル**: [KIF_to_usi.py](file:///c:/Users/hashimoto/shogiLLM/src/utils/KIF_to_usi.py)

KIF形式とUSI形式の相互変換。

| 関数 | 説明 |
|------|------|
| `kif_move_to_usi("７六歩(77)")` | KIF → USI（`"7g7f"`） |
| `usi_move_to_kif("7g7f", board)` | USI → KIF（`"▲７六歩"`） |
| `parse_kif_from_text(text)` | KIFテキスト → USI手順リスト |

```python
>>> from src.utils.KIF_to_usi import kif_move_to_usi, usi_move_to_kif
>>> kif_move_to_usi("７六歩(77)")
('7g7f', '7f')
>>> usi_move_to_kif("7g7f", board)
'▲７六歩'
```

📖 表記法の詳細: [kifu_notation.md](file:///c:/Users/hashimoto/shogiLLM/docs/utils/kifu_notation.md)

---

## dlshogi特徴量変換（dlshogi.py）

**ファイル**: [dlshogi.py](file:///c:/Users/hashimoto/shogiLLM/src/utils/dlshogi.py)

dlshogiの特徴量配列からSFEN文字列を復元。

| 関数 | 説明 |
|------|------|
| `dlfeatures_to_sfen(f1, f2)` | feature1, feature2 → SFEN |
