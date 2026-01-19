# -*- coding: utf-8 -*-
"""
対局シミュレーション機能のテスト

やねうら王ラッパー、Maia2ラッパー、統合シミュレーターのテストを行う。
"""

import pytest
from src.simulation.models import score_to_win_rate, SimulationResult, CandidateMove
from src.simulation.engine_wrapper import YaneuraouWrapper, EngineConfig
from src.simulation.maia2_wrapper import Maia2Wrapper, Maia2Config
from src.simulation.simulator import ShogiSimulator


# 初期局面のSFEN
STARTPOS_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"


class TestScoreToWinRate:
    """勝率変換関数のテスト。"""
    
    def test_zero_score_returns_half(self):
        """評価値0は勝率50%になる。"""
        result = score_to_win_rate(0)
        assert abs(result - 0.5) < 0.001
    
    def test_positive_score_above_half(self):
        """正の評価値は勝率50%以上になる。"""
        result = score_to_win_rate(300)
        assert result > 0.5
    
    def test_negative_score_below_half(self):
        """負の評価値は勝率50%以下になる。"""
        result = score_to_win_rate(-300)
        assert result < 0.5
    
    def test_large_score_near_one(self):
        """大きな評価値は勝率がほぼ100%になる。"""
        result = score_to_win_rate(3000)
        assert result > 0.99


class TestYaneuraouWrapper:
    """やねうら王ラッパーのテスト。"""
    
    def test_analyze_returns_candidates(self):
        """分析結果として候補手のリストが返る。"""
        with YaneuraouWrapper() as engine:
            candidates = engine.analyze(STARTPOS_SFEN)
            
            assert len(candidates) > 0
            assert all(isinstance(c, CandidateMove) for c in candidates)
            assert all(c.move != "" for c in candidates)
    
    def test_pv_positions_returns_sfens(self):
        """読み筋後の局面がSFEN形式で返る。"""
        with YaneuraouWrapper() as engine:
            candidates = engine.analyze(STARTPOS_SFEN)
            
            if candidates and candidates[0].pv:
                positions = engine.get_pv_positions(STARTPOS_SFEN, candidates[0].pv)
                assert len(positions) == len(candidates[0].pv)


class TestMaia2Wrapper:
    """Maia2ラッパーのテスト。"""
    
    def test_predict_returns_result(self):
        """予測結果が返る。"""
        with Maia2Wrapper() as maia2:
            result = maia2.predict(STARTPOS_SFEN)
            
            assert result.move != ""
            assert 0.0 <= result.probability <= 1.0
            assert 0.0 <= result.value <= 1.0
    
    def test_top_moves_returned(self):
        """上位候補手のリストが返る。"""
        config = Maia2Config(top_k=5)
        with Maia2Wrapper(config) as maia2:
            result = maia2.predict(STARTPOS_SFEN)
            
            assert len(result.top_moves) > 0
            # 合法手が5手未満の局面（例: 王手がかかっている状態）では
            # top_k=5 でも5手未満しか返らないため、<= 5 で判定
            assert len(result.top_moves) <= 5


class TestShogiSimulator:
    """統合シミュレーターのテスト。"""
    
    def test_analyze_returns_simulation_result(self):
        """分析結果としてSimulationResultが返る。"""
        with ShogiSimulator() as simulator:
            result = simulator.analyze(STARTPOS_SFEN)
            
            assert isinstance(result, SimulationResult)
            assert result.sfen == STARTPOS_SFEN
            assert result.best_move != ""
            assert result.human_move != ""
    
    def test_win_rates_are_comparable(self):
        """やねうら王とMaia2の勝率が比較可能な範囲内。"""
        with ShogiSimulator() as simulator:
            result = simulator.analyze(STARTPOS_SFEN)
            
            assert 0.0 <= result.best_win_rate <= 1.0
            assert 0.0 <= result.human_value <= 1.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
