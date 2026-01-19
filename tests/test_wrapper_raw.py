# -*- coding: utf-8 -*-
"""
ラッパー単体テスト - 生の評価値を確認

シミュレーターを介さずにラッパー単体で評価値/勝率を確認する。
"""

import pytest
from src.simulation.engine_wrapper import YaneuraouWrapper
from src.simulation.maia2_wrapper import Maia2Wrapper, Maia2Config


# テスト局面
POSITIONS = {
    "初期局面（先手番・互角）": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
    "角換わり中盤（後手番・後手不利）": "ln1g3nl/1rs2kg2/p2ppp1pp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L w B2Pb 28",
    "角換わり中盤2（先手番・先手有利）": "ln1g4l/1rs2kg2/p2pppnpp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L b B2Pb 29",
    "棒銀終盤2（後手番・後手有利）": "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/3S3R1/L3KG1NL w BSPbgnp 30",
    "棒銀終盤（先手番・先手不利）": "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/7R1/L1S1KG1NL b BSPbgnp 29",
}


class TestWrapperRawValues:
    """ラッパーの生データを確認するテスト。"""
    
    def test_yaneuraou_raw_values(self):
        """
        やねうら王の評価値と勝率を確認。

        注意:
            `YaneuraouWrapper.analyze()` はUSIのscore(cp/mate)を
            『先手有利=正、後手有利=負』に正規化して返す。
        """
        from src.simulation.engine_wrapper import EngineConfig
        
        # 探索時間を5秒に設定（精度向上）
        config = EngineConfig(byoyomi=5000)
        
        with YaneuraouWrapper(config) as engine:
            print("\n" + "=" * 60)
            print("やねうら王の生データ（評価値 = 先手視点）")
            print("=" * 60)
            
            for name, sfen in POSITIONS.items():
                candidates = engine.analyze(sfen)
                if candidates:
                    best = candidates[0]
                    print(f"\n【{name}】")
                    print(f"  手番: {'先手' if sfen.split()[1] == 'b' else '後手'}")
                    print(f"  評価値(cp): {best.score:+d}")
                    print(f"  勝率: {best.win_rate:.1%}")
                    print(f"  最善手: {best.move}")
    
    def test_maia2_raw_values(self):
        """
        Maia2のvalue（勝率）を確認。
        
        valueが先手視点か手番側視点かを確認する。
        """
        maia2_config = Maia2Config(rating_self=2700, rating_oppo=2700)
        
        with Maia2Wrapper(maia2_config) as maia2:
            print("\n" + "=" * 60)
            print("Maia2の生データ（value = ???視点）")
            print("=" * 60)
            
            for name, sfen in POSITIONS.items():
                result = maia2.predict(sfen)
                print(f"\n【{name}】")
                print(f"  手番: {'先手' if sfen.split()[1] == 'b' else '後手'}")
                print(f"  value: {result.value:.1%}")
                print(f"  最有力手: {result.move} ({result.probability:.1%})")
    
    def test_comparison_table(self):
        """
        やねうら王とMaia2の評価を並べて比較。
        """
        from src.simulation.engine_wrapper import EngineConfig
        
        # 探索時間を5秒に設定（精度向上）
        engine_config = EngineConfig(byoyomi=5000)
        maia2_config = Maia2Config(rating_self=2700, rating_oppo=2700)
        
        with YaneuraouWrapper(engine_config) as engine, Maia2Wrapper(maia2_config) as maia2:
            print("\n" + "=" * 80)
            print("比較表")
            print("=" * 80)
            print(f"{'局面':<25} | {'手番':^4} | {'やねうら王':^12} | {'Maia2':^8} | {'期待形勢'}")
            print("-" * 80)
            
            for name, sfen in POSITIONS.items():
                turn = "先手" if sfen.split()[1] == "b" else "後手"
                
                candidates = engine.analyze(sfen)
                engine_score = candidates[0].score if candidates else 0
                engine_wr = candidates[0].win_rate if candidates else 0.5
                
                maia2_result = maia2.predict(sfen)
                maia2_value = maia2_result.value
                
                # 局面名から期待形勢を抽出
                if "有利" in name:
                    expected = name.split("・")[1].replace("）", "")
                elif "不利" in name:
                    expected = name.split("・")[1].replace("）", "")
                else:
                    expected = "互角"
                
                print(f"{name[:25]:<25} | {turn:^4} | {engine_score:+5}cp ({engine_wr:5.1%}) | {maia2_value:5.1%} | {expected}")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
