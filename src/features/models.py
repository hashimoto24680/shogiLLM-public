"""
特徴抽出用データモデル

局面の特徴を表現するための各種データクラスを定義する。
"""

from __future__ import annotations

from dataclasses import dataclass, field

# MaterialAdvantage は既存の material.py からインポートする想定
# 循環インポートを避けるため、TYPE_CHECKING 内でのみインポート
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.features.material import MaterialAdvantage


@dataclass
class BasePiece:
    """駒の基本情報

    盤上の駒および持ち駒の基本的な属性を表現する。

    Attributes:
        piece_type: 駒の種類（"歩", "角", "飛" など）
        color: 手番（"先手" または "後手"）
        square: マスの日本語座標（"7七" など）
    """

    piece_type: str
    color: str
    square: str


@dataclass
class PieceInfo(BasePiece):
    """駒ごとの詳細情報（盤上の駒のみ）

    BasePieceを継承し、盤上の駒に特有の利き情報と活動度を追加する。

    Attributes:
        piece_type: 駒の種類（継承）
        color: 手番（継承）
        square: 日本語座標（継承）
        attack_squares: 利きがあるマスのリスト
        movable_squares: 実際に移動できるマス（自駒がいないマス）
        activity: 駒の働き（dlshogiでの評価値差分）
    """

    attack_squares: list[str] = field(default_factory=list)
    movable_squares: list[str] = field(default_factory=list)
    activity: int = 0


@dataclass
class SquareInfo:
    """マスごとの情報（81マス分）

    各マスの状態を表現する。駒の有無、隣接マス、利き情報を含む。

    Attributes:
        square: 日本語座標（"7七" など）
        piece: そのマスにいる駒（空なら None）
        adjacent: 隣接マス（先手視点の8方向、盤外は None）
            例: {"左上": "8六", "上": "7六", "右上": "6六", ...}
        direct_attackers: 直接利きを与えている駒のリスト
        indirect_attackers: 間接利き（飛角香が間に駒を挟んでいる）のリスト
        attack_balance: 利きのバランス（先手利き数 - 後手利き数）
    """

    square: str
    piece: PieceInfo | None = None
    adjacent: dict[str, str | None] = field(default_factory=dict)
    direct_attackers: list[BasePiece] = field(default_factory=list)
    indirect_attackers: list[BasePiece] = field(default_factory=list)
    attack_balance: int = 0


@dataclass
class HandPieces:
    """持ち駒

    どちらの手番がどの駒を何枚持っているかを表現する。

    Attributes:
        color: 手番（"先手" または "後手"）
        pieces: 駒種別の枚数（例: {"歩": 2, "角": 1}）
    """

    color: str
    pieces: dict[str, int] = field(default_factory=dict)


@dataclass
class KingSafety:
    """玉の安全度

    玉周辺の守備状況を数値化する。

    Attributes:
        color: 手番（"先手" または "後手"）
        king_square: 玉の位置（"8八" など）
        gold_count: 金駒スコア
            計算式: 隣接マスの金駒×2 + 2マス離れの金駒 - 2マス以内の敵駒
            ※金駒 = 金・銀
        density: 密集度（玉から2マス以内の自駒数 / 2マス以内のマス数、0.0〜1.0）
        safety_score: 総合安全度スコア
            計算式: gold_count * 10 + density * 50
    """

    color: str
    king_square: str
    gold_count: int = 0
    density: float = 0.0
    safety_score: int = 0


@dataclass
class CastlePattern:
    """囲い認識結果

    認識された囲いパターンを表現する。

    Attributes:
        name: 囲いの名前（"銀冠", "穴熊" など）
        color: 手番（"先手" または "後手"）
        confidence: 信頼度（0.0〜1.0）
    """

    name: str
    color: str
    confidence: float = 0.0


@dataclass
class StrategyPattern:
    """戦法認識結果

    認識された戦法パターンを表現する。

    Attributes:
        name: 戦法の名前（"四間飛車", "居飛車穴熊" など）
        color: 手番（"先手" または "後手"）
        confidence: 信頼度（0.0〜1.0）
    """

    name: str
    color: str
    confidence: float = 0.0


@dataclass
class StaticFeatures:
    """静的特徴

    ある1局面の全ての特徴を包括的に表現する。

    Attributes:
        sfen: 局面のSFEN文字列
        squares: 81マス分の情報（各マスにPieceInfoが含まれる）
        hand_pieces: 先手・後手の持ち駒
        material: 駒得情報（MaterialAdvantage）
        king_safety: 先手・後手の玉の安全度
        castles: 認識された囲いパターン
        strategies: 認識された戦法パターン
        dlshogi_score: dlshogiによる評価値（先手視点、正=先手有利）
        sente_activity_total: 先手の駒の働き合計
        gote_activity_total: 後手の駒の働き合計
    """

    sfen: str
    squares: list[SquareInfo] = field(default_factory=list)
    hand_pieces: list[HandPieces] = field(default_factory=list)
    material: "MaterialAdvantage | None" = None
    king_safety: list[KingSafety] = field(default_factory=list)
    castles: list[CastlePattern] = field(default_factory=list)
    strategies: list[StrategyPattern] = field(default_factory=list)
    dlshogi_score: int | None = None  # dlshogi評価値（先手視点）
    sente_activity_total: int = 0     # 先手の駒の働き合計
    gote_activity_total: int = 0      # 後手の駒の働き合計


@dataclass
class DynamicFeatures:
    """動的特徴（2つの局面の比較）

    2つの局面間の差分を表現する。

    Attributes:
        before: 変化前の静的特徴
        after: 変化後の静的特徴
        moves_between: 間の手順（あれば）。None は不明または直接比較を意味する
        material_change: 駒得の変化（after.advantage - before.advantage）
        sente_safety_change: 先手の安全度変化（after - before）
        gote_safety_change: 後手の安全度変化（after - before）
        score_change: dlshogi評価値の変化（after - before）
        material_change_description: 駒交換の説明（beforeからafterの変化）
        sente_activity_change: 先手の駒の働き合計の変化
        gote_activity_change: 後手の駒の働き合計の変化
    """

    before: StaticFeatures
    after: StaticFeatures
    moves_between: list[str] | None = None
    material_change: int = 0              # 駒得の変化（正=先手有利に変化）
    sente_safety_change: int = 0          # 先手の安全度変化
    gote_safety_change: int = 0           # 後手の安全度変化
    score_change: int | None = None       # 評価値の変化（やねうら王）
    material_change_description: str = "" # 駒交換の説明（beforeからafterの変化）
    sente_activity_change: int = 0        # 先手の駒の働き合計の変化
    gote_activity_change: int = 0         # 後手の駒の働き合計の変化
    promotions: list[str] = field(default_factory=list)  # 成駒発生リスト（例: ["先手角成", "後手歩成"]）

