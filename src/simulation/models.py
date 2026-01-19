# -*- coding: utf-8 -*-
"""
対局シミュレーション用データモデル

シミュレーション結果を格納するデータクラスを定義する。
"""

from dataclasses import dataclass
import math


@dataclass
class CandidateMove:
    """
    候補手の情報を格納するデータクラス。
    
    Attributes:
        move: USI形式の手（例: "7g7f"）
        score: 評価値（centipawn）
        win_rate: 勝率（0.0〜1.0）
        pv: 読み筋のリスト
    """
    move: str
    score: int
    win_rate: float
    pv: list[str]


@dataclass
class SimulationResult:
    """
    対局シミュレーションの結果を格納するデータクラス。
    
    やねうら王（強いAI）とMaia2（人間レベルAI）の
    両方の分析結果を統合して保持する。
    
    Attributes:
        sfen: 分析対象の局面（SFEN形式）
        
        best_move: やねうら王の最善手
        best_score: 評価値（centipawn）
        best_win_rate: 勝率に変換（0.0〜1.0）
        best_pv: 読み筋
        pv_positions: 読み筋を進めた後の各局面（SFEN）
        
        human_move: Maia2が予測した人間らしい手
        human_probability: その手を指す確率
        human_value: Maia2が予測した局面の勝率（0.0〜1.0）
    """
    sfen: str
    
    # やねうら王の結果
    best_move: str
    best_score: int
    best_win_rate: float
    best_pv: list[str]
    pv_positions: list[str]
    
    # Maia2の結果
    human_move: str
    human_probability: float
    human_value: float


def score_to_win_rate(score: int) -> float:
    """
    やねうら王の評価値（centipawn）を勝率に変換する。
    
    やねうら王公式サイトで推奨されているsigmoid関数を使用。
    定数600はPonanza由来で「Ponanza定数」とも呼ばれる。
    
    参考: https://yaneuraou.yaneu.com/2019/04/21/
    
    Args:
        score: 評価値（centipawn）。正の値は先手有利（先手視点に正規化済み）。
        
    Returns:
        勝率（0.0〜1.0）
    """
    return 1.0 / (1.0 + math.exp(-score / 600.0))


# ============================================================
# 形勢明確化シミュレーション用データ構造
# ============================================================

@dataclass
class MoveRecord:
    """
    最善応酬シミュレーションの1手分の記録。
    
    Attributes:
        sfen: この手を指した後の局面
        move: USI形式の手
        score: 評価値（centipawn）
        win_rate: 勝率（0.0〜1.0）
    """
    sfen: str
    move: str
    score: int
    win_rate: float


@dataclass
class TreeNode:
    """
    弱AI vs 強AI シミュレーションの樹形図ノード。
    
    Attributes:
        sfen: この局面（SFEN形式）
        move: 親ノードからこのノードに至った手（ルートはNone）
        depth: 対象局面からの深さ（ルートは0）
        strong_eval_win_rate: 強AI（やねうら王）評価 → 先手勝率
        weak_eval_win_rate: 弱AI（やねうら王20K）評価 → 先手勝率
        is_terminal: 終端局面か（両者の勝率差 ≤ 5% かつ 深さ ≥ 3）
        children: 子ノードのリスト
    """
    sfen: str
    move: str | None
    depth: int
    strong_eval_win_rate: float
    weak_eval_win_rate: float
    is_terminal: bool
    children: list["TreeNode"]


@dataclass
class SimulationTree:
    """
    形勢明確化シミュレーションの結果。
    
    Attributes:
        root_sfen: 対象局面（SFEN形式）
        best_line: 最善応酬（やねうら王 vs やねうら王）の手順
        tree: 弱AI vs 強AI の樹形図
    """
    root_sfen: str
    root_score: int | None
    best_line: list[MoveRecord]
    tree: TreeNode

