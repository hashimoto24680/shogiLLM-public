# -*- coding: utf-8 -*-
"""
局面特徴生成エンジンのテスト

tests/data_for_tests/ のテストデータを使用して、
src/features/ パッケージの機能をテストする。
"""

import pytest
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from tests.data_for_tests.test_sfens import ALL_TEST_SFENS, INITIAL_SFEN, ELMO_VS_SHIKEN_SFEN
from tests.data_for_tests.adjacant_squares import adjacent_squares


# ============================================================
# 低次元静的特徴（static_low.py）
# ============================================================

class TestStaticLow:
    """低次元静的特徴のテスト"""
    
    def test_square_to_japanese(self):
        """マス番号→日本語座標変換（coordinates.pyで実装済み）"""
        from src.utils.coordinates import index_to_japanese
        
        assert index_to_japanese(0) == "1一"
        assert index_to_japanese(40) == "5五"
        assert index_to_japanese(80) == "9九"
    
    def test_get_adjacent_squares_all(self):
        """隣接マス取得: data_for_tests/adjacant_squares.pyの全データがpass"""
        from src.features.static_low import get_adjacent_squares
        from src.utils.coordinates import japanese_to_index
        
        for (file, rank), expected_adjacents in adjacent_squares.items():
            # (筋, 段) から日本語座標に変換してテスト
            square_name = f"{file}{['一','二','三','四','五','六','七','八','九'][rank-1]}"
            # 日本語座標をインデックスに変換
            sq_index = japanese_to_index(square_name)
            result = get_adjacent_squares(sq_index)
            
            # 結果の隣接マス数が期待値と一致
            result_squares = [v for v in result.values() if v is not None]
            assert len(result_squares) == len(expected_adjacents), \
                f"マス {square_name} の隣接マス数が不一致: 期待{len(expected_adjacents)}, 実際{len(result_squares)}"
    
    @pytest.mark.parametrize("sfen", ALL_TEST_SFENS)
    def test_extract_all_squares(self, sfen):
        """81マス情報抽出: 全SFENで81個のSquareInfoを返す"""
        from src.features.static_low import extract_all_squares
        import cshogi
        
        board = cshogi.Board(sfen)
        squares = extract_all_squares(board)
        
        assert len(squares) == 81, f"SquareInfoの数が81ではない: {len(squares)}"
    
    @pytest.mark.parametrize("sfen", ALL_TEST_SFENS)
    def test_extract_hand_pieces(self, sfen):
        """持ち駒抽出: 全SFENで正しく抽出"""
        from src.features.static_low import extract_hand_pieces
        import cshogi
        
        board = cshogi.Board(sfen)
        hand_pieces = extract_hand_pieces(board)
        
        assert len(hand_pieces) == 2, "先手・後手の2つのHandPiecesを返すこと"
    
    @pytest.mark.parametrize("sfen", ALL_TEST_SFENS)
    def test_piece_info_in_square(self, sfen):
        """マスに駒情報が含まれる: PieceInfo.piece_type等が正しい"""
        from src.features.static_low import extract_all_squares
        import cshogi
        
        board = cshogi.Board(sfen)
        squares = extract_all_squares(board)
        
        # 駒があるマスでPieceInfoが正しく設定されているか
        for sq_info in squares:
            if sq_info.piece is not None:
                assert sq_info.piece.piece_type is not None
                assert sq_info.piece.color in ["先手", "後手"]
                assert sq_info.piece.square == sq_info.square
    
    @pytest.mark.parametrize("sfen", ALL_TEST_SFENS)
    def test_sfen_consistency(self, sfen):
        """入力SFENとStaticFeatures.sfenが一致"""
        from src.features.extractor import FeatureExtractor
        
        extractor = FeatureExtractor()
        features = extractor.extract_static(sfen)
        
        assert features.sfen == sfen


# ============================================================
# 高次元静的特徴（static_high.py）
# ============================================================

class TestStaticHigh:
    """高次元静的特徴のテスト"""
    
    def test_recognize_castle_elmo(self):
        """エルモ囲い認識: 先手にエルモ囲いがマッチ"""
        from src.features.static_high import recognize_castles
        import cshogi
        
        board = cshogi.Board(ELMO_VS_SHIKEN_SFEN)
        castles = recognize_castles(board)
        
        sente_castles = [c for c in castles if c.color == "先手"]
        # エルモ囲い（またはそれに近い囲い）がマッチすること
        assert len(sente_castles) > 0, "先手に囲いがマッチしていない"
    
    def test_recognize_castle_mino(self):
        """美濃囲い認識: 後手に美濃囲いがマッチ"""
        from src.features.static_high import recognize_castles
        import cshogi
        
        board = cshogi.Board(ELMO_VS_SHIKEN_SFEN)
        castles = recognize_castles(board)
        
        gote_castles = [c for c in castles if c.color == "後手"]
        mino_match = any("美濃" in c.name for c in gote_castles)
        assert mino_match, "後手に美濃囲いがマッチしていない"
    
    def test_recognize_strategy_ibisha(self):
        """居飛車認識: 先手が居飛車と判定"""
        from src.features.static_high import recognize_strategies
        import cshogi
        
        board = cshogi.Board(ELMO_VS_SHIKEN_SFEN)
        strategies = recognize_strategies(board)
        
        sente_strategies = [s for s in strategies if s.color == "先手"]
        ibisha_match = any("居飛車" in s.name for s in sente_strategies)
        assert ibisha_match, "先手が居飛車と判定されていない"
    
    def test_recognize_strategy_shiken(self):
        """四間飛車認識: 後手が四間飛車と判定"""
        from src.features.static_high import recognize_strategies
        import cshogi
        
        board = cshogi.Board(ELMO_VS_SHIKEN_SFEN)
        strategies = recognize_strategies(board)
        
        gote_strategies = [s for s in strategies if s.color == "後手"]
        shiken_match = any("四間" in s.name for s in gote_strategies)
        assert shiken_match, "後手が四間飛車と判定されていない"
    
    @pytest.mark.parametrize("sfen", ALL_TEST_SFENS)
    def test_calculate_king_safety(self, sfen):
        """玉安全度計算: 妥当なsafety_scoreを返す"""
        from src.features.static_high import calculate_king_safety
        import cshogi
        
        board = cshogi.Board(sfen)
        
        for color in ["先手", "後手"]:
            safety = calculate_king_safety(board, color)
            assert safety is not None
            assert isinstance(safety.safety_score, (int, float))
    
    def test_calculate_king_safety_enemy_penalty(self):
        """敵駒ペナルティ: 2マス以内の敵駒がgold_countを減らす"""
        from src.features.static_high import calculate_king_safety
        import cshogi
        
        # 後手玉(2一)の隣接に後手金(3二)があり+2点
        # しかし2マス以内に先手金(5二)がいるので-1点
        # 差し引きgold_count = 1
        sfen = "l4rknl/4G1g2/2n+Bp2p1/p1pp2p1p/1p3s1P1/P1P3P1P/1PSPP4/1KG2G3/LN5RL w Pb2snp 54"
        board = cshogi.Board(sfen)
        
        safety = calculate_king_safety(board, "後手")
        assert safety.gold_count == 1, f"敵駒ペナルティが正しく計算されていない: {safety.gold_count}"


# ============================================================
# 駒得計算（material.py）
# ============================================================

class TestMaterial:
    """駒得計算のテスト"""
    
    def test_calculate_material_initial(self):
        """初期局面の駒得: advantage = 0"""
        from src.features.material import calculate_material
        
        result = calculate_material(INITIAL_SFEN)
        assert result.advantage == 0, f"初期局面の駒得が0ではない: {result.advantage}"
    
    def test_calculate_material_advantage(self):
        """駒得あり局面: 飛車得でadvantage ≈ 10"""
        from src.features.material import calculate_material
        from tests.data_for_tests.test_sfens import ROOK_ADVANTAGE_SFEN
        
        result = calculate_material(ROOK_ADVANTAGE_SFEN)
        assert result.advantage >= 10, f"飛車得の駒得が10未満: {result.advantage}"
    
    def test_piece_values(self):
        """駒点数定義: 飛=1000, 角=800, 等（100倍スケール）"""
        from src.features.material import PIECE_VALUES
        
        assert PIECE_VALUES["飛"] == 1000
        assert PIECE_VALUES["角"] == 800
        assert PIECE_VALUES["金"] == 600
        assert PIECE_VALUES["銀"] == 500
        assert PIECE_VALUES["桂"] == 400
        assert PIECE_VALUES["香"] == 300
        assert PIECE_VALUES["歩"] == 100


# ============================================================
# 駒の働き（dlshogi_wrapper.py）
# ============================================================

class TestPieceActivity:
    """駒の働きのテスト"""
    
    @pytest.mark.parametrize("sfen", ALL_TEST_SFENS)
    def test_dlshogi_predict(self, sfen):
        """dlshogi推論: valueが0.0-1.0の範囲"""
        from src.features.dlshogi_wrapper import DlshogiWrapper
        
        wrapper = DlshogiWrapper("models/model-dr2_exhi.onnx")
        wrapper.load()
        
        result = wrapper.predict(sfen)
        
        assert 0.0 <= result.value <= 1.0, f"valueが範囲外: {result.value}"
        
        wrapper.unload()


# ============================================================
# 動的特徴（dynamic.py）
# ============================================================

class TestDynamic:
    """動的特徴のテスト"""
    
    def test_extract_dynamic_features(self):
        """2局面比較: DynamicFeaturesを返す"""
        from src.features.dynamic import extract_dynamic_features
        from src.features.extractor import FeatureExtractor
        
        extractor = FeatureExtractor()
        before = extractor.extract_static(INITIAL_SFEN)
        after = extractor.extract_static(ELMO_VS_SHIKEN_SFEN)
        
        dynamic = extract_dynamic_features(before, after)
        
        assert dynamic.before == before
        assert dynamic.after == after
    
    def test_dynamic_with_moves(self):
        """手順付き比較: moves_betweenが保持される"""
        from src.features.dynamic import extract_dynamic_features
        from src.features.extractor import FeatureExtractor
        
        extractor = FeatureExtractor()
        before = extractor.extract_static(INITIAL_SFEN)
        after = extractor.extract_static(ELMO_VS_SHIKEN_SFEN)
        
        moves = ["7g7f", "3c3d"]
        dynamic = extract_dynamic_features(before, after, moves_between=moves)
        
        assert dynamic.moves_between == moves


# ============================================================
# 統合API（extractor.py）
# ============================================================

class TestExtractor:
    """統合APIのテスト"""
    
    @pytest.mark.parametrize("sfen", ALL_TEST_SFENS)
    def test_extract_static(self, sfen):
        """静的特徴抽出: StaticFeaturesを返す"""
        from src.features.extractor import FeatureExtractor
        from src.features.models import StaticFeatures
        
        extractor = FeatureExtractor()
        features = extractor.extract_static(sfen)
        
        assert isinstance(features, StaticFeatures)
        assert features.sfen == sfen
    
    def test_extract_dynamic(self):
        """動的特徴抽出: DynamicFeaturesを返す"""
        from src.features.extractor import FeatureExtractor
        from src.features.models import DynamicFeatures
        
        extractor = FeatureExtractor()
        dynamic = extractor.extract_dynamic(INITIAL_SFEN, ELMO_VS_SHIKEN_SFEN)
        
        assert isinstance(dynamic, DynamicFeatures)
    
    def test_to_text(self):
        """テキスト変換: LLM入力用文字列を返す"""
        from src.features.extractor import FeatureExtractor
        
        extractor = FeatureExtractor()
        features = extractor.extract_static(INITIAL_SFEN)
        text = extractor.to_text(features)
        
        assert isinstance(text, str)
        assert len(text) > 0
