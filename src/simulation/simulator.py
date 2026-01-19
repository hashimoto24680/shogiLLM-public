# -*- coding: utf-8 -*-
"""
将棋対局シミュレーター

やねうら王（強いAI）とMaia2（人間レベルAI）を統合し、
局面分析の結果を一つにまとめて返す。
"""

from src.simulation.models import SimulationResult
from src.simulation.engine_wrapper import YaneuraouWrapper, EngineConfig
from src.simulation.maia2_wrapper import Maia2Wrapper, Maia2Config


class ShogiSimulator:
    """
    将棋対局シミュレーター。
    
    やねうら王とMaia2を使用して局面を分析し、
    最善手と人間らしい手を比較する。
    
    Attributes:
        yaneuraou: やねうら王ラッパー
        maia2: Maia2ラッパー
    """
    
    def __init__(
        self,
        engine_config: EngineConfig | None = None,
        maia2_config: Maia2Config | None = None,
    ):
        """
        シミュレーターを初期化する。
        
        Args:
            engine_config: やねうら王の設定
            maia2_config: Maia2の設定
        """
        self.yaneuraou = YaneuraouWrapper(engine_config)
        self.maia2 = Maia2Wrapper(maia2_config)
    
    def connect(self) -> None:
        """
        両方のAIに接続する。
        """
        self.yaneuraou.connect()
        self.maia2.load()
    
    def disconnect(self) -> None:
        """
        両方のAIとの接続を終了する。
        """
        self.yaneuraou.disconnect()
        self.maia2.unload()
    
    def analyze(self, sfen: str) -> SimulationResult:
        """
        局面を分析し、やねうら王とMaia2の結果を統合して返す。
        
        Args:
            sfen: 分析対象の局面（SFEN形式）
            
        Returns:
            SimulationResult: 統合された分析結果
        """
        # やねうら王で分析
        candidates = self.yaneuraou.analyze(sfen)
        
        if candidates:
            best = candidates[0]
            best_move = best.move
            best_score = best.score
            best_win_rate = best.win_rate
            best_pv = best.pv
            pv_positions = self.yaneuraou.get_pv_positions(sfen, best_pv)
        else:
            best_move = ""
            best_score = 0
            best_win_rate = 0.5
            best_pv = []
            pv_positions = []
        
        # Maia2で分析
        maia2_result = self.maia2.predict(sfen)
        
        return SimulationResult(
            sfen=sfen,
            best_move=best_move,
            best_score=best_score,
            best_win_rate=best_win_rate,
            best_pv=best_pv,
            pv_positions=pv_positions,
            human_move=maia2_result.move,
            human_probability=maia2_result.probability,
            human_value=maia2_result.value,
        )
    
    def __enter__(self):
        """コンテキストマネージャーのenter。"""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーのexit。"""
        self.disconnect()
        return False
