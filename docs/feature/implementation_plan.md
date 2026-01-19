# 局面特徴生成エンジンの実装

LLMへの入力として使用する「言語的な特徴量」を生成するエンジンを実装する。シミュレーションで得られた局面情報（SFEN）から、静的特徴（低次元・高次元）と動的特徴（差分）を抽出する。

---

## Proposed Changes

### Feature Extraction パッケージ（新規）

```
src/
├── simulation/          # 既存
└── features/            # 新規：局面特徴抽出
    ├── __init__.py
    ├── models.py        # データモデル
    ├── static_low.py    # 低次元静的特徴
    ├── static_high.py   # 高次元静的特徴
    ├── dynamic.py       # 動的特徴（差分）
    ├── patterns/        # 囲い・戦法パターン定義
    │   ├── __init__.py
    │   ├── castles.py   # 囲いパターン
    │   └── strategies.py # 戦法パターン
    └── extractor.py     # 統合API
```

---

#### [NEW] [models.py](file:///c:/Users/hashimoto/shogiLLM/src/features/models.py)

特徴抽出用のデータクラスを定義。

```python
@dataclass
class BasePiece:
    """駒の基本情報"""
    piece_type: str     # "歩", "角", "飛" etc.
    color: str          # "先手" or "後手"
    square: str         # "7七" etc. (日本語座標)

@dataclass
class PieceInfo(BasePiece):
    """駒ごとの詳細情報（盤上の駒のみ）"""
    attack_squares: list[str]   # 利きがあるマス
    movable_squares: list[str]  # 実際に移動できるマス（自駒のいないマス）
    activity: int               # 駒の働き（dlshogiでの評価値差分）

@dataclass
class SquareInfo:
    """マスごとの情報（81マス分）"""
    square: str                         # "7七" etc. (日本語座標)
    piece: PieceInfo | None             # そのマスにいる駒（空なら None）
    # 隣接マス（先手視点の8方向、盤外は None）
    adjacent: dict[str, str | None]     # {"左上": "8六", "上": "7六", ...}
    direct_attackers: list[BasePiece]   # 直接利きを与えている駒（BasePieceで十分）
    indirect_attackers: list[BasePiece] # 間接利き（飛角香が間に駒を挟んでいる）
    attack_balance: int                 # 先手利き数 - 後手利き数

@dataclass
class HandPieces:
    """持ち駒"""
    color: str
    pieces: dict[str, int]  # {"歩": 2, "角": 1, ...}

@dataclass
class KingSafety:
    """玉の安全度"""
    color: str              # "先手" or "後手"
    king_square: str        # 玉の位置（"8八" etc.）
    gold_count: int         # 金駒スコア = 隣接マスの金駒×2 + 2マス離れの金駒 - 2マス以内の敵駒
                            # ※金駒 = 金・銀
    density: float          # 密集度 = 玉から2マス以内の自駒数 / 2マス以内のマス数（0.0〜1.0）
    safety_score: int       # 総合安全度 = gold_count * 10 + density * 50

@dataclass
class CastlePattern:
    """囲い認識結果"""
    name: str           # "銀冠", "穴熊" etc.
    color: str
    confidence: float   # 0.0〜1.0

@dataclass
class StrategyPattern:
    """戦法認識結果"""
    name: str           # "四間飛車", "居飛車穴熊" etc.
    color: str
    confidence: float   # 0.0〜1.0

@dataclass
class StaticFeatures:
    """静的特徴"""
    sfen: str
    squares: list[SquareInfo]           # 81マス分（各マスにPieceInfoが含まれる）
    hand_pieces: list[HandPieces]       # 先手・後手の持ち駒
    material: MaterialAdvantage         # 駒得情報（src/features/material.py）
    king_safety: list[KingSafety]       # 先手・後手の玉の安全度
    castles: list[CastlePattern]        # 認識された囲い
    strategies: list[StrategyPattern]   # 認識された戦法

@dataclass
class DynamicFeatures:
    """動的特徴（2つの局面の比較）"""
    before: StaticFeatures
    after: StaticFeatures
    moves_between: list[str] | None  # 間の手順（あれば）。None = 不明/直接比較
    material_change: int             # 駒得の変化（after - before）
    sente_safety_change: int         # 先手の安全度変化
    gote_safety_change: int          # 後手の安全度変化
```

---

#### [NEW] [static_low.py](file:///c:/Users/hashimoto/shogiLLM/src/features/static_low.py)

cshogiを使用した低次元静的特徴の抽出。

```python
def square_to_japanese(sq: int) -> str:
    """マス番号を日本語座標に変換（例: 44 -> "5五"）"""

def get_adjacent_squares(sq: int) -> dict[str, str | None]:
    """8方向の隣接マスを取得（盤外はNone）"""

def extract_square_info(board: cshogi.Board, sq: int) -> SquareInfo:
    """1マスの情報を抽出（駒、利き、隣接マス）"""

def extract_all_squares(board: cshogi.Board) -> list[SquareInfo]:
    """81マス全ての情報を抽出"""

def extract_hand_pieces(board: cshogi.Board) -> list[HandPieces]:
    """先手・後手の持ち駒を抽出"""
```

---

#### [NEW] [static_high.py](file:///c:/Users/hashimoto/shogiLLM/src/features/static_high.py)

高次元静的特徴の抽出。

```python
def recognize_castles(board: cshogi.Board) -> list[CastlePattern]:
    """囲いを認識（patterns/castles.pyのALL_CASTLESを使用）"""

def recognize_strategies(board: cshogi.Board) -> list[StrategyPattern]:
    """戦法を認識（patterns/strategies.pyのALL_STRATEGIESを使用）"""

def calculate_king_safety(board: cshogi.Board, color: str) -> KingSafety:
    """玉の安全度を計算
    - gold_count: 周囲の金駒（金・成駒）の枚数
    - density: 玉から2マス以内の自駒の存在比率
    - enemy_penalty: 敵駒による減点
    """

def calculate_piece_activity(board: cshogi.Board) -> dict[str, int]:
    """各駒の働きを計算（dlshogi_wrapper使用）"""
```

---

#### [EXISTING] [patterns/castles.py](file:///c:/Users/hashimoto/shogiLLM/src/features/patterns/castles.py)

囲いパターンの定義（40種以上）。`CastleDefinition`と`CastleCondition`で定義。

| カテゴリ | 囲い例 |
|---------|-------|
| 矢倉系 | 金矢倉, 銀矢倉, 片矢倉, 総矢倉, 矢倉穴熊, 菊水矢倉, 菱矢倉 |
| 雁木系 | 雁木囲い, ボナンザ囲い |
| 美濃系 | 美濃囲い, 高美濃, 銀冠, 銀美濃, ダイヤモンド美濃, 片美濃 |
| 左美濃系 | 左美濃, 天守閣美濃, 四枚美濃 |
| 舟囲い系 | 舟囲い |
| 穴熊系 | 居飛車穴熊, 振り飛車穴熊, 松尾流, 銀冠穴熊, ビッグ4 |
| その他 | 金無双, 中住まい, 中原囲い, アヒル囲い |

---

#### [EXISTING] [patterns/strategies.py](file:///c:/Users/hashimoto/shogiLLM/src/features/patterns/strategies.py)

戦法パターンの定義（39種）。`StrategyDefinition`と`StrategyCondition`で定義。

---

#### [NEW] [dynamic.py](file:///c:/Users/hashimoto/shogiLLM/src/features/dynamic.py)

動的特徴の抽出（2つの局面の比較）。

```python
def extract_dynamic_features(
    before: StaticFeatures,
    after: StaticFeatures,
    moves_between: list[str] | None = None
) -> DynamicFeatures:
    """2つの静的特徴を比較してDynamicFeaturesを生成"""
```

---

#### [NEW] [extractor.py](file:///c:/Users/hashimoto/shogiLLM/src/features/extractor.py)

統合API。

```python
class FeatureExtractor:
    """局面特徴生成エンジン"""
    
    def __init__(self, dlshogi_model_path: str = None):
        """dlshogiモデルパスを指定（駒の働き計算用）"""
    
    def extract_static(self, sfen: str) -> StaticFeatures:
        """静的特徴を抽出（81マス情報、持ち駒、駒得、玉安全度、囲い、戦法）"""
        
    def extract_dynamic(
        self, 
        sfen_before: str, 
        sfen_after: str,
        moves_between: list[str] | None = None
    ) -> DynamicFeatures:
        """2つの局面の静的特徴を比較"""
        
    def to_text(self, features: StaticFeatures | DynamicFeatures) -> str:
        """特徴をLLM入力用テキストに変換"""
```

---

#### [MODIFY] [README.md](file:///c:/Users/hashimoto/shogiLLM/README.md)

Phase 2のステータスを更新。

---

## Verification Plan

詳細は [docs/feature_verification_plan.md](file:///c:/Users/hashimoto/shogiLLM/docs/feature_verification_plan.md) を参照。


