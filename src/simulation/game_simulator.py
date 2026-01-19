# -*- coding: utf-8 -*-
"""
形勢明確化シミュレーター

対象局面から形勢がはっきりした局面を生成する。
- シミュレーション1: 最善応酬（やねうら王 vs やねうら王）
- シミュレーション2: 弱AI vs 強AI 樹形図
"""

from dataclasses import dataclass

import cshogi
from cshogi import Board

from src.simulation.models import (
    MoveRecord,
    TreeNode,
    SimulationTree,
    score_to_win_rate,
    CandidateMove,
)
from src.simulation.engine_wrapper import YaneuraouWrapper, EngineConfig
from src.simulation.maia2_wrapper import Maia2Wrapper, Maia2Config, Maia2Prediction


# 定数
BEST_LINE_MOVES = 10       # 最善応酬の手数
TREE_MAX_DEPTH = 10        # 樹形図の最大深さ
TREE_MIN_DEPTH = 3         # 終端判定の最小深さ
CANDIDATE_PROB_THRESHOLD = 0.10  # 候補手の確率閾値
CANDIDATE_MAX_COUNT = 3    # 候補手の最大数
CONVERGENCE_THRESHOLD = 0.05     # 勝率収束閾値（5%）
WEAK_ENGINE_NODES = 20000  # 弱AIエンジンの探索ノード数


@dataclass
class PositionEvaluation:
    """
    局面評価の結果（全AIの結果をまとめて保持）。
    
    Attributes:
        sfen: 局面（SFEN形式）
        strong_candidates: 強AIやねうら王の候補手リスト
        weak_candidates: 弱AIやねうら王（20Kノード）の候補手リスト
        maia2_result: Maia2の予測結果（手予測用）
    """
    sfen: str
    strong_candidates: list[CandidateMove]
    weak_candidates: list[CandidateMove]
    maia2_result: Maia2Prediction


class GameSimulator:
    """
    形勢明確化シミュレーター。
    
    対象局面から2種類のシミュレーションを実行し、
    形勢がはっきりした末端局面を生成する。
    
    - 強AI: やねうら王（通常探索）
    - 弱AI: やねうら王（20Kノード制限）+ Maia2（手予測）
    """
    
    def __init__(
        self,
        engine_config: EngineConfig | None = None,
        maia2_config: Maia2Config | None = None,
    ):
        """
        シミュレーターを初期化する。
        
        Args:
            engine_config: 強AI（やねうら王）の設定
            maia2_config: Maia2の設定（手予測用）
        """
        # 強AI（通常探索）
        self.strong_engine = YaneuraouWrapper(engine_config)
        
        # 弱AI（20Kノード制限）- Maia2のvalueが正常動作しないため代用
        weak_config = EngineConfig(nodes=WEAK_ENGINE_NODES)
        self.weak_engine = YaneuraouWrapper(weak_config)
        
        # Maia2（手予測用）
        self.maia2 = Maia2Wrapper(maia2_config)
        
        # Maia2側（ルート局面の手番）を記録
        self._maia2_turn: int | None = None  # cshogi.BLACK or cshogi.WHITE
    
    def connect(self) -> None:
        """AIに接続する。"""
        self.strong_engine.connect()
        self.weak_engine.connect()
        self.maia2.load()
    
    def disconnect(self) -> None:
        """AIとの接続を終了する。"""
        self.strong_engine.disconnect()
        self.weak_engine.disconnect()
        self.maia2.unload()
    
    def simulate(self, sfen: str) -> SimulationTree:
        """
        対象局面から形勢明確化シミュレーションを実行する。
        
        Args:
            sfen: 対象局面（SFEN形式）
            
        Returns:
            SimulationTree: シミュレーション結果
        """
        # ルート局面の手番を記録（これがMaia2側）
        board = Board()
        board.set_sfen(sfen)
        self._maia2_turn = board.turn
        
        # ルート局面の評価を取得（やねうら王スコア）
        root_eval = self._evaluate_position(sfen)
        root_score = None
        if root_eval.strong_candidates:
            root_score = root_eval.strong_candidates[0].score
        
        # シミュレーション1: 最善応酬
        best_line = self._simulate_best_line(sfen)
        
        # シミュレーション2: 弱AI vs 強AI 樹形図
        tree = self._build_tree(sfen)
        
        return SimulationTree(
            root_sfen=sfen,
            root_score=root_score,
            best_line=best_line,
            tree=tree,
        )
    
    def _evaluate_position(self, sfen: str) -> PositionEvaluation:
        """
        局面を全AIで評価する（1回の呼び出しで全て取得）。
        
        Args:
            sfen: 局面（SFEN形式）
            
        Returns:
            PositionEvaluation: 全AIの評価結果
        """
        strong_candidates = self.strong_engine.analyze(sfen)
        weak_candidates = self.weak_engine.analyze(sfen)
        maia2_result = self.maia2.predict(sfen)
        
        return PositionEvaluation(
            sfen=sfen,
            strong_candidates=strong_candidates,
            weak_candidates=weak_candidates,
            maia2_result=maia2_result,
        )
    
    def _get_maia2_side_win_rate(
        self,
        evaluation: PositionEvaluation
    ) -> tuple[float, float]:
        """
        両AIの評価を勝率に変換して返す。

        注意:
            `YaneuraouWrapper` 側で score(cp/mate) を
            『先手有利=正』に正規化しているため、ここで得られる win_rate は
            すでに「先手の勝率（0.0〜1.0）」になっている。
            そのため手番や深さによる反転は不要。

        Returns:
            (strong_eval_win_rate, weak_eval_win_rate):
                - strong_eval_win_rate: 強AI（やねうら王）評価 → 先手勝率
                - weak_eval_win_rate: 弱AI（やねうら王20K）評価 → 先手勝率
        """
        if evaluation.strong_candidates:
            strong_win_rate = evaluation.strong_candidates[0].win_rate
        else:
            strong_win_rate = 0.5

        # Maia2のvalueが正常動作しないため、弱AIエンジンで代替
        if evaluation.weak_candidates:
            weak_win_rate = evaluation.weak_candidates[0].win_rate
        else:
            weak_win_rate = 0.5

        return strong_win_rate, weak_win_rate
    
    def _simulate_best_line(self, sfen: str) -> list[MoveRecord]:
        """
        最善応酬シミュレーション（やねうら王 vs やねうら王）。
        
        Args:
            sfen: 開始局面
            
        Returns:
            手順の記録リスト
        """
        records = []
        board = Board()
        board.set_sfen(sfen)
        current_sfen = sfen
        
        for _ in range(BEST_LINE_MOVES):
            # 強AIで最善手を取得
            candidates = self.strong_engine.analyze(current_sfen)
            if not candidates:
                break
            
            best = candidates[0]
            
            # 手を進める
            board.push_usi(best.move)
            current_sfen = board.sfen()
            
            records.append(MoveRecord(
                sfen=current_sfen,
                move=best.move,
                score=best.score,
                win_rate=best.win_rate,
            ))
        
        return records
    
    def _build_tree(self, sfen: str) -> TreeNode:
        """
        弱AI vs 強AI の樹形図を構築する。
        
        Args:
            sfen: 開始局面
            
        Returns:
            樹形図のルートノード
        """
        # ルートノードの評価を取得
        evaluation = self._evaluate_position(sfen)
        strong_eval, weak_eval = self._get_maia2_side_win_rate(evaluation)
        
        root = TreeNode(
            sfen=sfen,
            move=None,
            depth=0,
            strong_eval_win_rate=strong_eval,
            weak_eval_win_rate=weak_eval,
            is_terminal=False,
            children=[],
        )
        
        # 再帰的に樹形図を構築（ルートの評価結果を渡す）
        self._expand_node(root, is_maia2_turn=True, evaluation=evaluation)
        
        return root
    
    def _expand_node(
        self, 
        node: TreeNode, 
        is_maia2_turn: bool,
        evaluation: PositionEvaluation | None = None,
    ) -> None:
        """
        ノードを展開する（再帰）。
        
        Args:
            node: 展開するノード
            is_maia2_turn: Maia2の手番か
            evaluation: 既に取得済みの評価結果（あれば再利用）
        """
        # 深さ制限チェック
        if node.depth >= TREE_MAX_DEPTH:
            node.is_terminal = True
            return
        
        # 終端条件チェック（深さ3以上かつ勝率収束）
        if node.depth >= TREE_MIN_DEPTH:
            diff = abs(node.strong_eval_win_rate - node.weak_eval_win_rate)
            if diff <= CONVERGENCE_THRESHOLD:
                node.is_terminal = True
                return
        
        # 評価結果がなければ取得
        if evaluation is None:
            evaluation = self._evaluate_position(node.sfen)
        
        if is_maia2_turn:
            # Maia2の手番: 確率10%以上の手を最大3つ
            candidates = self._get_maia2_candidates(evaluation.maia2_result)
        else:
            # 強AIの手番: 最善手1つのみ
            candidates = self._get_yaneuraou_best(evaluation.strong_candidates)
        
        if not candidates:
            node.is_terminal = True
            return
        
        for move in candidates:
            # 手を進めて新しい局面を生成
            board = Board()
            board.set_sfen(node.sfen)
            board.push_usi(move)
            child_sfen = board.sfen()
            
            # 子ノードの評価を取得（1回の呼び出しで両方取得）
            child_evaluation = self._evaluate_position(child_sfen)
            strong_eval, weak_eval = self._get_maia2_side_win_rate(child_evaluation)
            
            child = TreeNode(
                sfen=child_sfen,
                move=move,
                depth=node.depth + 1,
                strong_eval_win_rate=strong_eval,
                weak_eval_win_rate=weak_eval,
                is_terminal=False,
                children=[],
            )
            node.children.append(child)
            
            # 再帰的に展開（評価結果を渡す）
            self._expand_node(
                child, 
                is_maia2_turn=not is_maia2_turn,
                evaluation=child_evaluation,
            )
    
    def _get_maia2_candidates(self, maia2_result: Maia2Prediction) -> list[str]:
        """
        Maia2の候補手を取得（確率10%以上、最大3つ）。
        
        Args:
            maia2_result: Maia2の予測結果
            
        Returns:
            候補手のリスト（USI形式）
        """
        candidates = []
        
        for move, prob in maia2_result.top_moves:
            if prob >= CANDIDATE_PROB_THRESHOLD:
                candidates.append(move)
            if len(candidates) >= CANDIDATE_MAX_COUNT:
                break
        
        return candidates
    
    def _get_yaneuraou_best(self, engine_candidates: list[CandidateMove]) -> list[str]:
        """
        やねうら王の最善手を取得。
        
        Args:
            engine_candidates: やねうら王の候補手リスト
            
        Returns:
            最善手のリスト（1つのみ）
        """
        if engine_candidates:
            return [engine_candidates[0].move]
        return []
    
    def __enter__(self):
        """コンテキストマネージャーのenter。"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーのexit。"""
        self.disconnect()
        return False
