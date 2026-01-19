# -*- coding: utf-8 -*-
"""
形勢明確化シミュレーターのテスト
"""

import pytest
from src.simulation.models import MoveRecord, TreeNode, SimulationTree
from src.simulation.game_simulator import GameSimulator
from src.simulation.maia2_wrapper import Maia2Config


# 初期局面のSFEN（先手番）
STARTPOS_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"

# ============================================================
# 勝率変換テスト用局面（先手/後手 × 有利/不利 の4パターン）
# ============================================================

# パターン1: Maia2が後手で不利（角換わり中盤）
# 後手番、後手不利 → Maia2側勝率 < 0.5
KAKUGAWARI_CHUBAN_SFEN = "ln1g3nl/1rs2kg2/p2ppp1pp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L w B2Pb 28"

# パターン2: Maia2が先手で有利（角換わり中盤2）
# 先手番、先手有利 → Maia2側勝率 > 0.5
KAKUGAWARI_CHUBAN2_SFEN = "ln1g4l/1rs2kg2/p2pppnpp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L b B2Pb 29"

# パターン3: Maia2が後手で有利（棒銀終盤2）
# 後手番、後手が極めて有利 → Maia2側勝率 > 0.5
BOUGIN_SHUUBAN2_SFEN = "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/3S3R1/L3KG1NL w BSPbgnp 30"

# パターン4: Maia2が先手で不利（棒銀終盤）
# 先手番、先手が極めて不利 → Maia2側勝率 < 0.5
BOUGIN_SHUUBAN_SFEN = "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/7R1/L1S1KG1NL b BSPbgnp 29"


# 高レートMaia2設定（形勢認識の精度を上げる）
HIGH_RATE_MAIA2_CONFIG = Maia2Config(rating_self=2700, rating_oppo=2700)


class TestGameSimulator:
    """GameSimulatorのテスト。"""
    
    def test_simulate_returns_simulation_tree(self):
        """simulate()がSimulationTreeを返す。"""
        with GameSimulator() as sim:
            result = sim.simulate(STARTPOS_SFEN)
            
            assert isinstance(result, SimulationTree)
            assert result.root_sfen == STARTPOS_SFEN
    
    def test_best_line_has_moves(self):
        """最善応酬に手順が含まれる。"""
        with GameSimulator() as sim:
            result = sim.simulate(STARTPOS_SFEN)
            
            assert len(result.best_line) > 0
            assert all(isinstance(r, MoveRecord) for r in result.best_line)
    
    def test_tree_has_root(self):
        """樹形図にルートノードがある。"""
        with GameSimulator() as sim:
            result = sim.simulate(STARTPOS_SFEN)
            
            assert isinstance(result.tree, TreeNode)
            assert result.tree.sfen == STARTPOS_SFEN
            assert result.tree.depth == 0
            assert result.tree.move is None
    
    def test_tree_has_children(self):
        """樹形図に子ノードがある（Maia2の候補手）。"""
        with GameSimulator() as sim:
            result = sim.simulate(STARTPOS_SFEN)
            
            # 初期局面からは候補手があるはず
            assert len(result.tree.children) > 0


class TestWinRateConversion:
    """
    勝率変換の正確性テスト。
    
    先手/後手 × 有利/不利 の4パターンをテスト。
    """
    
    def test_pattern1_gote_disadvantage(self):
        """
        パターン1: Maia2が後手で不利（角換わり中盤）
        
        局面: ln1g3nl/1rs2kg2/p2ppp1pp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L w B2Pb 28
        - 後手番（w = white）
        - 後手が不利
        - 先手勝率 > 0.5
        """
        with GameSimulator(maia2_config=HIGH_RATE_MAIA2_CONFIG) as sim:
            result = sim.simulate(KAKUGAWARI_CHUBAN_SFEN)
            
            strong_wr = result.tree.strong_eval_win_rate
            weak_wr = result.tree.weak_eval_win_rate
            
            print(f"\n=== パターン1: 角換わり中盤（後手が不利）===")
            print(f"強AI（5秒）→ 先手勝率: {strong_wr:.1%}")
            print(f"弱AI（20Kノード）→ 先手勝率: {weak_wr:.1%}")
            
            assert strong_wr > 0.5, f"強AI: {strong_wr:.1%} (> 50%のはず)"
            assert weak_wr > 0.5, f"弱AI: {weak_wr:.1%} (> 50%のはず)"
    
    def test_pattern2_sente_advantage(self):
        """
        パターン2: Maia2が先手で有利（角換わり中盤2）
        
        局面: ln1g4l/1rs2kg2/p2pppnpp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L b B2Pb 29
        - 先手番（b = black）
        - 先手が有利
        - 先手勝率 > 0.5
        """
        with GameSimulator(maia2_config=HIGH_RATE_MAIA2_CONFIG) as sim:
            result = sim.simulate(KAKUGAWARI_CHUBAN2_SFEN)
            
            strong_wr = result.tree.strong_eval_win_rate
            weak_wr = result.tree.weak_eval_win_rate
            
            print(f"\n=== パターン2: 角換わり中盤2（先手が有利）===")
            print(f"強AI（5秒）→ 先手勝率: {strong_wr:.1%}")
            print(f"弱AI（20Kノード）→ 先手勝率: {weak_wr:.1%}")
            
            assert strong_wr > 0.5, f"強AI: {strong_wr:.1%} (> 50%のはず)"
            assert weak_wr > 0.5, f"弱AI: {weak_wr:.1%} (> 50%のはず)"
    
    def test_pattern3_gote_advantage(self):
        """
        パターン3: Maia2が後手で有利（棒銀終盤2）
        
        局面: ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/3S3R1/L3KG1NL w BSPbgnp 30
        - 後手番（w = white）
        - 後手が極めて有利
        - 先手勝率 < 0.5
        """
        with GameSimulator(maia2_config=HIGH_RATE_MAIA2_CONFIG) as sim:
            result = sim.simulate(BOUGIN_SHUUBAN2_SFEN)
            
            strong_wr = result.tree.strong_eval_win_rate
            weak_wr = result.tree.weak_eval_win_rate
            
            print(f"\n=== パターン3: 棒銀終盤2（後手が極めて有利）===")
            print(f"強AI（5秒）→ 先手勝率: {strong_wr:.1%}")
            print(f"弱AI（20Kノード）→ 先手勝率: {weak_wr:.1%}")
            
            assert strong_wr < 0.5, f"強AI: {strong_wr:.1%} (< 50%のはず)"
            assert weak_wr < 0.5, f"弱AI: {weak_wr:.1%} (< 50%のはず)"
    
    def test_pattern4_sente_disadvantage(self):
        """
        パターン4: Maia2が先手で不利（棒銀終盤）
        
        局面: ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/7R1/L1S1KG1NL b BSPbgnp 29
        - 先手番（b = black）
        - 先手が極めて不利
        - 先手勝率 < 0.5
        """
        with GameSimulator(maia2_config=HIGH_RATE_MAIA2_CONFIG) as sim:
            result = sim.simulate(BOUGIN_SHUUBAN_SFEN)
            
            strong_wr = result.tree.strong_eval_win_rate
            weak_wr = result.tree.weak_eval_win_rate
            
            print(f"\n=== パターン4: 棒銀終盤（先手が極めて不利）===")
            print(f"強AI（5秒）→ 先手勝率: {strong_wr:.1%}")
            print(f"弱AI（20Kノード）→ 先手勝率: {weak_wr:.1%}")
            
            assert strong_wr < 0.5, f"強AI: {strong_wr:.1%} (< 50%のはず)"
            assert weak_wr < 0.5, f"弱AI: {weak_wr:.1%} (< 50%のはず)"
    
    def test_startpos_near_equal(self):
        """初期局面は互角付近のはず。"""
        with GameSimulator() as sim:
            result = sim.simulate(STARTPOS_SFEN)
            
            strong_wr = result.tree.strong_eval_win_rate
            weak_wr = result.tree.weak_eval_win_rate
            
            print(f"\n=== 初期局面（互角）===")
            print(f"強AI（5秒）→ 先手勝率: {strong_wr:.1%}")
            print(f"弱AI（20Kノード）→ 先手勝率: {weak_wr:.1%}")
            
            assert 0.4 <= strong_wr <= 0.6, f"強AI評価が互角範囲外: {strong_wr:.1%}"
            assert 0.4 <= weak_wr <= 0.7, f"弱AI評価が互角範囲外: {weak_wr:.1%}"


class TestTreeStructure:
    """樹形図構造のテスト。"""
    
    def test_max_candidates_per_node(self):
        """各ノードの候補手が最大3つ以下。"""
        with GameSimulator() as sim:
            result = sim.simulate(STARTPOS_SFEN)
            
            # Maia2の手番（偶数深さ）で候補手が3つ以下
            assert len(result.tree.children) <= 3
    
    def test_yaneuraou_turn_has_one_child(self):
        """やねうら王の手番では子ノードが1つ。"""
        with GameSimulator() as sim:
            result = sim.simulate(STARTPOS_SFEN)
            
            # 深さ1のノード（やねうら王の応手後）を確認
            for child in result.tree.children:
                if child.children:
                    # 深さ1からの子は1つのはず（やねうら王は最善手1つ）
                    assert len(child.children) == 1, \
                        f"やねうら王の手番で子ノードが{len(child.children)}個（1つのはず）"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
