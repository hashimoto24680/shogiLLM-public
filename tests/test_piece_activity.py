# -*- coding: utf-8 -*-
"""
駒の働き計算のテスト

Test First (AI-TDD) に従い、実装前にテストを作成。

Note: src.features.piece_activity モジュールは未実装のため、このテストはスキップされます。
"""

import pytest
import numpy as np

from src.features.dlshogi_wrapper import DlshogiWrapper, FEATURES1_NUM

try:
    from src.features.piece_activity import (
        mask_piece_effect,
        mask_single_piece_effect,
        PieceType,
        SENTE_EFFECT_OFFSET,
        GOTE_EFFECT_OFFSET,
        calculate_piece_activity,
        calculate_single_piece_activity,
        calculate_all_piece_activities,
        parse_square,
        square_to_index,
        PieceActivity,
    )
except ImportError:
    pytest.skip(
        "src.features.piece_activity モジュールは未実装",
        allow_module_level=True
    )

# 使用するモデルパス（docs/piece_activity_plan.mdで指定）
MODEL_PATH = "models/model-dr2_exhi.onnx"

# テスト用SFEN
STARTPOS_SFEN = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
KAKUGAWARI_CHUBAN_SFEN = "ln1g3nl/1rs2kg2/p2ppp1pp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L w B2Pb 28"


class TestMaskPieceEffect:
    """mask_piece_effect関数のテスト"""

    @pytest.fixture
    def sample_features(self):
        """テスト用のサンプル特徴量を生成"""
        import cshogi
        wrapper = DlshogiWrapper(MODEL_PATH)
        wrapper.load()
        board = cshogi.Board()
        features1, _ = wrapper.make_features(board)
        wrapper.unload()
        return features1

    def test_mask_sente_pawn_effect(self, sample_features):
        """先手の歩の利きをマスクできること"""
        masked = mask_piece_effect(sample_features, PieceType.PAWN, "sente")
        
        # 元の特徴量は変更されていないこと
        assert sample_features is not masked
        
        # 歩の利きチャンネルがゼロになっていること
        pawn_effect_channel = SENTE_EFFECT_OFFSET + PieceType.PAWN.value
        assert np.all(masked[pawn_effect_channel, :, :] == 0.0)

    def test_mask_gote_rook_effect(self, sample_features):
        """後手の飛車の利きをマスクできること"""
        masked = mask_piece_effect(sample_features, PieceType.ROOK, "gote")
        
        # 飛車の利きチャンネルがゼロになっていること
        rook_effect_channel = GOTE_EFFECT_OFFSET + PieceType.ROOK.value
        assert np.all(masked[rook_effect_channel, :, :] == 0.0)

    def test_mask_preserves_other_channels(self, sample_features):
        """マスク対象以外のチャンネルは変更されないこと"""
        masked = mask_piece_effect(sample_features, PieceType.PAWN, "sente")
        
        pawn_effect_channel = SENTE_EFFECT_OFFSET + PieceType.PAWN.value
        for i in range(FEATURES1_NUM):
            if i != pawn_effect_channel:
                np.testing.assert_array_equal(
                    masked[i, :, :],
                    sample_features[i, :, :]
                )

    def test_invalid_side_raises_error(self, sample_features):
        """不正なside指定でエラーになること"""
        with pytest.raises(ValueError):
            mask_piece_effect(sample_features, PieceType.PAWN, "invalid")


class TestCalculatePieceActivity:
    """calculate_piece_activity関数のテスト"""

    @pytest.fixture
    def wrapper(self):
        """ラッパーインスタンスを作成"""
        w = DlshogiWrapper(MODEL_PATH)
        w.load()
        yield w
        w.unload()

    def test_calculate_piece_activity_returns_list(self, wrapper):
        """駒の働き計算が結果リストを返すこと"""
        sfen = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
        result = calculate_piece_activity(wrapper, sfen)
        
        # 結果がリストであること
        assert isinstance(result, list)
        
        # 結果がPieceActivity型を含むこと
        assert len(result) > 0
        assert all(isinstance(item, PieceActivity) for item in result)

    def test_piece_activity_has_expected_fields(self, wrapper):
        """PieceActivityが必要なフィールドを持つこと"""
        sfen = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
        result = calculate_piece_activity(wrapper, sfen)
        
        for activity in result:
            assert hasattr(activity, 'piece_type')
            assert hasattr(activity, 'side')
            assert hasattr(activity, 'activity_value')

    def test_activity_value_is_numeric(self, wrapper):
        """activity_valueが数値であること"""
        sfen = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
        result = calculate_piece_activity(wrapper, sfen)
        
        for activity in result:
            assert isinstance(activity.activity_value, (int, float))


class TestParseSquare:
    """座標解析のテスト"""

    def test_parse_square_2f(self):
        """2fは2筋6段目（２六）"""
        file, rank = parse_square("2f")
        assert file == 2
        assert rank == 6

    def test_parse_square_7g(self):
        """7gは7筋7段目（７七）"""
        file, rank = parse_square("7g")
        assert file == 7
        assert rank == 7

    def test_parse_square_5e(self):
        """5eは5筋5段目（５五）"""
        file, rank = parse_square("5e")
        assert file == 5
        assert rank == 5

    def test_invalid_square_raises_error(self):
        """不正な座標でエラー"""
        with pytest.raises(ValueError):
            parse_square("xx")

    def test_square_to_index_5e(self):
        """5eのインデックスが正しいこと"""
        idx = square_to_index(5, 5)
        # 5筋5段目: (9-5) + (5-1)*9 = 4 + 36 = 40
        assert idx == 40


class TestSinglePieceActivity:
    """単一駒の働き計算のテスト"""

    @pytest.fixture
    def wrapper(self):
        w = DlshogiWrapper(MODEL_PATH)
        w.load()
        yield w
        w.unload()

    def test_single_piece_activity_sente_pawn(self, wrapper):
        """初期局面で2七の歩の働きを計算できること"""
        result = calculate_single_piece_activity(wrapper, STARTPOS_SFEN, "2g")
        
        assert result.square == "2g"
        assert result.piece_type == PieceType.PAWN
        assert result.side == "sente"
        assert isinstance(result.activity_value, int)
        print(f"2七歩の働き: {result.activity_value}")

    def test_single_piece_activity_rook(self, wrapper):
        """初期局面で2八の飛車の働きを計算できること"""
        result = calculate_single_piece_activity(wrapper, STARTPOS_SFEN, "2h")
        
        assert result.square == "2h"
        assert result.piece_type == PieceType.ROOK
        assert result.side == "sente"
        print(f"2八飛の働き: {result.activity_value}")

    def test_single_piece_activity_empty_square_raises(self, wrapper):
        """空マスを指定するとエラー"""
        with pytest.raises(ValueError):
            calculate_single_piece_activity(wrapper, STARTPOS_SFEN, "5e")

    def test_calculate_all_piece_activities(self, wrapper):
        """全駒の働きを計算できること"""
        results = calculate_all_piece_activities(wrapper, STARTPOS_SFEN)
        
        # 初期局面は40枚の駒がある
        assert len(results) == 40
        
        # すべてPieceActivityであること
        assert all(isinstance(r, PieceActivity) for r in results)
        
        # すべて座標が設定されていること
        assert all(r.square != "" for r in results)
        
        # 先手と後手の駒があること
        sente_count = sum(1 for r in results if r.side == "sente")
        gote_count = sum(1 for r in results if r.side == "gote")
        assert sente_count == 20
        assert gote_count == 20
        
        print(f"全駒の働き計算完了: {len(results)}駒")

    def test_kakugawari_position_rook_activity(self, wrapper):
        """角換わり中盤局面の飛車の働き"""
        # 3dにある先手の飛車
        result = calculate_single_piece_activity(wrapper, KAKUGAWARI_CHUBAN_SFEN, "3d")
        
        print(f"3四飛の働き: {result.activity_value} (駒種: {result.piece_name}, 手番: {result.side})")
        assert result.piece_type == PieceType.ROOK
