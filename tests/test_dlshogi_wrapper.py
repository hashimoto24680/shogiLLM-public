# -*- coding: utf-8 -*-
"""
dlshogiラッパーのテスト

Test First (AI-TDD) に従い、実装前にテストを作成。
"""

import pytest
import numpy as np

from src.features.dlshogi_wrapper import (
    DlshogiWrapper,
    DlshogiPrediction,
    CandidateMove,
    win_rate_to_score,
)

# 使用するモデルパス（docs/piece_activity_plan.mdで指定）
MODEL_PATH = "models/model-dr2_exhi.onnx"


class TestWinRateToScore:
    """勝率→評価値変換のテスト"""

    def test_fifty_percent_returns_zero(self):
        """勝率50%は評価値0に近い値を返す"""
        score = win_rate_to_score(0.5)
        assert score == 0

    def test_high_win_rate_returns_positive(self):
        """高い勝率は正の評価値を返す"""
        score = win_rate_to_score(0.8)
        assert score > 0

    def test_low_win_rate_returns_negative(self):
        """低い勝率は負の評価値を返す"""
        score = win_rate_to_score(0.2)
        assert score < 0

    def test_edge_case_zero(self):
        """勝率0は-33000を返す"""
        score = win_rate_to_score(0.0)
        assert score == -33000

    def test_edge_case_one(self):
        """勝率1.0は33000を返す"""
        score = win_rate_to_score(1.0)
        assert score == 33000


class TestDlshogiWrapper:
    """DlshogiWrapperのテスト"""

    @pytest.fixture
    def wrapper(self):
        """ラッパーインスタンスを作成"""
        w = DlshogiWrapper(MODEL_PATH)
        w.load()
        yield w
        w.unload()

    def test_predict_initial_position(self, wrapper):
        """初期局面で予測できること"""
        sfen = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
        result = wrapper.predict(sfen)

        # DlshogiPrediction型であること
        assert isinstance(result, DlshogiPrediction)

        # valueは0~1の範囲
        assert 0.0 <= result.value <= 1.0

        # policyは2187要素
        assert result.policy.shape == (2187,)

        # 評価値が範囲内
        assert -33000 <= result.score <= 33000

    def test_predict_from_features(self, wrapper):
        """特徴量から直接予測できること"""
        import cshogi

        board = cshogi.Board()
        features1, features2 = wrapper.make_features(board)

        # 特徴量の形状確認
        assert features1.shape == (62, 9, 9)
        assert features2.shape == (57, 9, 9)

        # 予測
        result = wrapper.predict_from_features(features1, features2)
        assert 0.0 <= result.value <= 1.0

    def test_make_features_shape(self, wrapper):
        """make_featuresが正しい形状の特徴量を返すこと"""
        import cshogi

        board = cshogi.Board()
        features1, features2 = wrapper.make_features(board)

        assert features1.shape == (62, 9, 9)
        assert features2.shape == (57, 9, 9)
        assert features1.dtype == np.float32
        assert features2.dtype == np.float32

    def test_context_manager(self):
        """コンテキストマネージャで使用できること"""
        with DlshogiWrapper(MODEL_PATH) as wrapper:
            sfen = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
            result = wrapper.predict(sfen)
            assert 0.0 <= result.value <= 1.0

    def test_model_not_found(self):
        """存在しないモデルパスでFileNotFoundErrorが発生すること"""
        wrapper = DlshogiWrapper("nonexistent/model.onnx")
        with pytest.raises(FileNotFoundError):
            wrapper.load()


class TestCoordinateSystem:
    """
    座標系検証テスト。

    dlshogiのpolicyラベルが正しい座標系でUSI形式の手に
    変換されているか確認する。
    """

    # テスト用SFEN（test_game_simulator.pyから）
    STARTPOS_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
    KAKUGAWARI_CHUBAN_SFEN = "ln1g3nl/1rs2kg2/p2ppp1pp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L w B2Pb 28"

    @pytest.fixture
    def wrapper(self):
        w = DlshogiWrapper(MODEL_PATH)
        w.load()
        yield w
        w.unload()

    def test_get_top_moves_initial_position(self, wrapper):
        """初期局面の上位5手が取得できること"""
        candidates, value = wrapper.get_top_moves(self.STARTPOS_SFEN, top_n=5)

        # 5手取得できること
        assert len(candidates) == 5

        # すべてCandidateMove型であること
        assert all(isinstance(c, CandidateMove) for c in candidates)

        # USI形式の手が取得できていること（数字+アルファベット形式）
        for c in candidates:
            assert len(c.usi) >= 4, f"USI形式ではない: {c.usi}"
            print(f"  {c.usi}: {c.policy_prob:.1%}")

        # 確率の合計が1に近いこと（上位5手なので1未満だが相当量あるはず）
        total_prob = sum(c.policy_prob for c in candidates)
        print(f"上位5手の確率合計: {total_prob:.1%}")
        assert total_prob > 0.5, f"上位5手の確率が低すぎる: {total_prob:.1%}"

    def test_initial_position_common_moves(self, wrapper):
        """
        初期局面の上位手に一般的な初手が含まれること。

        座標系が正しければ、7g7f（７六歩）, 2g2f（２六歩）などの
        一般的な初手がpolicyに含まれるはず。
        """
        candidates, _ = wrapper.get_top_moves(self.STARTPOS_SFEN, top_n=10)

        usi_moves = [c.usi for c in candidates]
        print(f"上位10手: {usi_moves}")

        # 一般的な初手のいずれかが含まれるべき
        common_opening_moves = [
            "7g7f",  # ７六歩
            "2g2f",  # ２六歩
            "2h7h",  # ７八飛（向かい飛車）
            "7i6h",  # ６八銀
            "3i4h",  # ４八銀
            "5g5f",  # ５六歩
        ]

        found = [m for m in common_opening_moves if m in usi_moves]
        print(f"一般的な初手で見つかったもの: {found}")

        assert len(found) >= 1, \
            f"一般的な初手が含まれていない。座標系がずれている可能性。上位10手: {usi_moves}"

    def test_kakugawari_position(self, wrapper):
        """角換わり中盤局面で候補手が取得できること"""
        candidates, value = wrapper.get_top_moves(self.KAKUGAWARI_CHUBAN_SFEN, top_n=5)

        assert len(candidates) == 5

        usi_moves = [c.usi for c in candidates]
        print(f"角換わり中盤の上位5手: {usi_moves}")
        print(f"評価値（後手視点）: {value:.1%}")

        # 候補手がすべて有効なUSI形式であること
        for c in candidates:
            # USI形式: [1-9][a-i][1-9][a-i](+)?
            assert len(c.usi) >= 4

    def test_value_range(self, wrapper):
        """評価値が妥当な範囲にあること"""
        # 初期局面は互角付近のはず
        _, value_start = wrapper.get_top_moves(self.STARTPOS_SFEN)
        print(f"初期局面の勝率: {value_start:.1%}")
        assert 0.4 <= value_start <= 0.6, f"初期局面が互角ではない: {value_start:.1%}"

        # 角換わり中盤（後手不利）
        _, value_kaku = wrapper.get_top_moves(self.KAKUGAWARI_CHUBAN_SFEN)
        print(f"角換わり中盤（後手番）の勝率: {value_kaku:.1%}")
        # 後手不利なので0.5未満のはず
        assert value_kaku < 0.5, f"後手不利のはずが: {value_kaku:.1%}"
