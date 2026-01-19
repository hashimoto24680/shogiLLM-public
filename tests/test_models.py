"""
tests/test_models.py

models.py のデータクラスが正しく動作することを確認するテスト。

各クラスの基本的なインスタンス化と属性アクセスを検証する。
"""

import pytest

from src.features.models import (
    BasePiece,
    CastlePattern,
    DynamicFeatures,
    HandPieces,
    KingSafety,
    PieceInfo,
    SquareInfo,
    StaticFeatures,
    StrategyPattern,
)


class TestBasePiece:
    """BasePiece クラスのテスト"""

    def test_create_base_piece(self) -> None:
        """BasePiece を正しく作成できる"""
        piece = BasePiece(piece_type="歩", color="先手", square="7七")

        assert piece.piece_type == "歩"
        assert piece.color == "先手"
        assert piece.square == "7七"

    def test_create_various_pieces(self) -> None:
        """様々な種類の駒を作成できる"""
        pieces = [
            BasePiece(piece_type="角", color="先手", square="8八"),
            BasePiece(piece_type="飛", color="後手", square="2二"),
            BasePiece(piece_type="金", color="先手", square="4九"),
        ]

        assert len(pieces) == 3
        assert pieces[0].piece_type == "角"
        assert pieces[1].color == "後手"
        assert pieces[2].square == "4九"


class TestPieceInfo:
    """PieceInfo クラスのテスト"""

    def test_create_piece_info_with_defaults(self) -> None:
        """PieceInfo をデフォルト値で作成できる"""
        piece = PieceInfo(piece_type="歩", color="先手", square="7七")

        assert piece.piece_type == "歩"
        assert piece.attack_squares == []
        assert piece.movable_squares == []
        assert piece.activity == 0

    def test_create_piece_info_with_attacks(self) -> None:
        """PieceInfo を利き情報付きで作成できる"""
        piece = PieceInfo(
            piece_type="角",
            color="先手",
            square="8八",
            attack_squares=["7七", "6六", "5五"],
            movable_squares=["7七", "6六"],
            activity=50,
        )

        assert len(piece.attack_squares) == 3
        assert len(piece.movable_squares) == 2
        assert piece.activity == 50


class TestSquareInfo:
    """SquareInfo クラスのテスト"""

    def test_create_empty_square(self) -> None:
        """空のマス情報を作成できる"""
        square = SquareInfo(square="5五")

        assert square.square == "5五"
        assert square.piece is None
        assert square.adjacent == {}
        assert square.direct_attackers == []
        assert square.indirect_attackers == []
        assert square.attack_balance == 0

    def test_create_square_with_piece(self) -> None:
        """駒のあるマス情報を作成できる"""
        piece = PieceInfo(piece_type="歩", color="先手", square="7六")
        square = SquareInfo(
            square="7六",
            piece=piece,
            adjacent={"上": "7五", "下": "7七"},
            attack_balance=1,
        )

        assert square.piece is not None
        assert square.piece.piece_type == "歩"
        assert len(square.adjacent) == 2
        assert square.attack_balance == 1


class TestHandPieces:
    """HandPieces クラスのテスト"""

    def test_create_hand_pieces_empty(self) -> None:
        """空の持ち駒を作成できる"""
        hand = HandPieces(color="先手")

        assert hand.color == "先手"
        assert hand.pieces == {}

    def test_create_hand_pieces_with_pieces(self) -> None:
        """持ち駒を作成できる"""
        hand = HandPieces(color="先手", pieces={"歩": 3, "角": 1})

        assert hand.pieces["歩"] == 3
        assert hand.pieces["角"] == 1


class TestKingSafety:
    """王の安全度クラスのテスト"""

    def test_create_king_safety_default(self) -> None:
        """KingSafety をデフォルト値で作成できる"""
        safety = KingSafety(color="先手", king_square="5九")

        assert safety.color == "先手"
        assert safety.king_square == "5九"
        assert safety.gold_count == 0
        assert safety.density == 0.0
        assert safety.safety_score == 0

    def test_create_king_safety_with_values(self) -> None:
        """KingSafety を具体的な値で作成できる"""
        # 計算式: gold_count * 10 + density * 50
        # 2 * 10 + 0.5 * 50 = 20 + 25 = 45
        safety = KingSafety(
            color="先手",
            king_square="8八",
            gold_count=2,
            density=0.5,
            safety_score=45,
        )

        assert safety.gold_count == 2
        assert safety.density == 0.5
        assert safety.safety_score == 45


class TestCastlePattern:
    """CastlePattern クラスのテスト"""

    def test_create_castle_pattern(self) -> None:
        """囲いパターンを作成できる"""
        castle = CastlePattern(name="銀冠", color="先手", confidence=0.95)

        assert castle.name == "銀冠"
        assert castle.color == "先手"
        assert castle.confidence == 0.95


class TestStrategyPattern:
    """StrategyPattern クラスのテスト"""

    def test_create_strategy_pattern(self) -> None:
        """戦法パターンを作成できる"""
        strategy = StrategyPattern(name="四間飛車", color="後手", confidence=0.8)

        assert strategy.name == "四間飛車"
        assert strategy.color == "後手"
        assert strategy.confidence == 0.8


class TestStaticFeatures:
    """StaticFeatures クラスのテスト"""

    def test_create_static_features_minimal(self) -> None:
        """最小限の StaticFeatures を作成できる"""
        features = StaticFeatures(sfen="lnsgkgsnl/...")

        assert features.sfen == "lnsgkgsnl/..."
        assert features.squares == []
        assert features.hand_pieces == []
        assert features.material is None
        assert features.king_safety == []
        assert features.castles == []
        assert features.strategies == []

    def test_create_static_features_with_data(self) -> None:
        """データ付きの StaticFeatures を作成できる"""
        squares = [SquareInfo(square="5五")]
        hand_pieces = [HandPieces(color="先手", pieces={"歩": 1})]
        king_safety = [KingSafety(color="先手", king_square="5九")]
        castles = [CastlePattern(name="矢倉", color="先手", confidence=0.9)]
        strategies = [StrategyPattern(name="居飛車", color="先手", confidence=1.0)]

        features = StaticFeatures(
            sfen="test_sfen",
            squares=squares,
            hand_pieces=hand_pieces,
            king_safety=king_safety,
            castles=castles,
            strategies=strategies,
        )

        assert len(features.squares) == 1
        assert len(features.hand_pieces) == 1
        assert len(features.king_safety) == 1
        assert len(features.castles) == 1
        assert len(features.strategies) == 1


class TestDynamicFeatures:
    """DynamicFeatures クラスのテスト"""

    def test_create_dynamic_features(self) -> None:
        """動的特徴を作成できる"""
        before = StaticFeatures(sfen="before_sfen")
        after = StaticFeatures(sfen="after_sfen")

        dynamic = DynamicFeatures(
            before=before,
            after=after,
            moves_between=["7g7f", "3c3d"],
        )

        assert dynamic.before.sfen == "before_sfen"
        assert dynamic.after.sfen == "after_sfen"
        assert dynamic.moves_between == ["7g7f", "3c3d"]

    def test_create_dynamic_features_without_moves(self) -> None:
        """手順なしの動的特徴を作成できる"""
        before = StaticFeatures(sfen="before")
        after = StaticFeatures(sfen="after")

        dynamic = DynamicFeatures(before=before, after=after)

        assert dynamic.moves_between is None
