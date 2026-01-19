"""
tests/test_static_low.py

低次元静的特徴抽出のテスト。

cshogiを使用して81マスの情報と持ち駒を抽出する関数をテストする。
"""

import pytest
import cshogi

from src.features.static_low import (
    square_to_japanese,
    get_adjacent_squares,
    extract_square_info,
    extract_all_squares,
    extract_hand_pieces,
)
from src.features.models import SquareInfo, PieceInfo, HandPieces


class TestSquareToJapanese:
    """マス番号を日本語座標に変換する関数のテスト"""

    def test_corner_squares(self) -> None:
        """盤の四隅を正しく変換できる"""
        assert square_to_japanese(0) == "1一"
        assert square_to_japanese(8) == "1九"
        assert square_to_japanese(72) == "9一"
        assert square_to_japanese(80) == "9九"

    def test_center_square(self) -> None:
        """中央のマスを正しく変換できる"""
        assert square_to_japanese(40) == "5五"

    def test_common_squares(self) -> None:
        """よく使われるマスを正しく変換できる"""
        assert square_to_japanese(60) == "7七"  # 角の初期位置に近い
        assert square_to_japanese(44) == "5九"  # 先手玉の初期位置


class TestGetAdjacentSquares:
    """8方向の隣接マスを取得する関数のテスト"""

    def test_center_square_has_all_neighbors(self) -> None:
        """中央のマスは8方向全て隣接マスがある"""
        adjacent = get_adjacent_squares(40)  # 5五

        assert len(adjacent) == 8
        assert adjacent["上"] is not None
        assert adjacent["下"] is not None
        assert adjacent["左"] is not None
        assert adjacent["右"] is not None
        assert adjacent["左上"] is not None
        assert adjacent["右上"] is not None
        assert adjacent["左下"] is not None
        assert adjacent["右下"] is not None

    def test_corner_square_has_limited_neighbors(self) -> None:
        """角のマスは一部の隣接マスがNone"""
        adjacent = get_adjacent_squares(0)  # 1一

        # 1一は左・左上・左下・上がない
        assert adjacent["左"] is None
        assert adjacent["左上"] is None
        assert adjacent["左下"] is None
        assert adjacent["上"] is None
        # 右・右下・下はある
        assert adjacent["右"] is not None
        assert adjacent["下"] is not None
        assert adjacent["右下"] is not None

    def test_edge_square(self) -> None:
        """辺のマスは一部の隣接マスがNone"""
        adjacent = get_adjacent_squares(4)  # 1五（上辺の中央）

        # 左がない（1筋）
        assert adjacent["左"] is None
        assert adjacent["左上"] is None
        assert adjacent["左下"] is None
        # 上下右はある
        assert adjacent["上"] is not None
        assert adjacent["下"] is not None
        assert adjacent["右"] is not None


class TestExtractSquareInfo:
    """1マスの情報を抽出する関数のテスト"""

    def test_empty_square(self) -> None:
        """空のマスの情報を正しく抽出できる"""
        board = cshogi.Board()
        # 5五（初期局面で空）
        info = extract_square_info(board, 40)

        assert info.square == "5五"
        assert info.piece is None

    def test_square_with_piece(self) -> None:
        """駒のあるマスの情報を正しく抽出できる"""
        board = cshogi.Board()
        # 7七（先手歩の初期位置）
        info = extract_square_info(board, 60)

        assert info.square == "7七"
        assert info.piece is not None
        assert info.piece.piece_type == "歩"
        assert info.piece.color == "先手"
        assert info.piece.square == "7七"

    def test_square_with_gote_piece(self) -> None:
        """後手の駒があるマスを正しく抽出できる"""
        board = cshogi.Board()
        # 7三（後手歩の初期位置）
        info = extract_square_info(board, 56)

        assert info.piece is not None
        assert info.piece.color == "後手"

    def test_adjacent_squares_included(self) -> None:
        """隣接マス情報が含まれている"""
        board = cshogi.Board()
        info = extract_square_info(board, 40)

        assert len(info.adjacent) == 8


class TestExtractAllSquares:
    """81マス全ての情報を抽出する関数のテスト"""

    def test_returns_81_squares(self) -> None:
        """81マス分の情報を返す"""
        board = cshogi.Board()
        squares = extract_all_squares(board)

        assert len(squares) == 81

    def test_each_square_has_correct_type(self) -> None:
        """各マスがSquareInfo型である"""
        board = cshogi.Board()
        squares = extract_all_squares(board)

        for sq in squares:
            assert isinstance(sq, SquareInfo)

    def test_initial_position_piece_count(self) -> None:
        """初期配置で正しい数の駒がある"""
        board = cshogi.Board()
        squares = extract_all_squares(board)

        pieces_on_board = [sq for sq in squares if sq.piece is not None]
        # 初期配置: 先手20枚 + 後手20枚 = 40枚
        assert len(pieces_on_board) == 40


class TestExtractHandPieces:
    """持ち駒を抽出する関数のテスト"""

    def test_initial_position_no_hand(self) -> None:
        """初期局面では持ち駒がない"""
        board = cshogi.Board()
        hands = extract_hand_pieces(board)

        assert len(hands) == 2  # 先手と後手
        assert hands[0].color == "先手"
        assert hands[1].color == "後手"
        # 全て0枚
        assert all(count == 0 for count in hands[0].pieces.values())
        assert all(count == 0 for count in hands[1].pieces.values())

    def test_with_hand_pieces(self) -> None:
        """持ち駒がある局面を正しく抽出できる"""
        # 先手が飛車を持っている局面
        sfen = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b R 1"
        board = cshogi.Board(sfen)
        hands = extract_hand_pieces(board)

        assert hands[0].pieces.get("飛", 0) == 1

    def test_returns_hand_pieces_type(self) -> None:
        """HandPieces型のリストを返す"""
        board = cshogi.Board()
        hands = extract_hand_pieces(board)

        for hand in hands:
            assert isinstance(hand, HandPieces)
