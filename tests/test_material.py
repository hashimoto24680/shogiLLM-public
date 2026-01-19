# -*- coding: utf-8 -*-
"""
駒得description機能のテスト

material.pyの_generate_exchange_description関数をテストする。
"""

import pytest
from src.features.material import calculate_material


class TestMaterialDescription:
    """駒交換descriptionのテスト。"""

    def test_one_pawn_loss(self):
        """先手の歩損。"""
        sfen = "ln1g3nl/1ks1gr3/1ppppsb1p/p4ppp1/4S4/P1P1P1P2/1P1P1P2P/1BKS3R1/LNG1G2NL b p 3"
        result = calculate_material(sfen)
        assert result.description == "先手の歩損"

    def test_two_pawn_loss(self):
        """先手の二歩損。"""
        sfen = "ln1g3nl/1ks1gr3/1ppppsb1p/p4p1p1/4S1p2/P1P1P4/1P1P1P2P/1BKS3R1/LNG1G2NL b 2p 5"
        result = calculate_material(sfen)
        assert result.description == "先手の二歩損"

    def test_silver_gain(self):
        """先手の銀得。"""
        sfen = "ln1g3nl/1ks1gr3/1pppp1bpp/p3SppP1/9/P1P1P1P2/1P1P1P2P/1BKS3R1/LNG1G2NL w S 4"
        result = calculate_material(sfen)
        assert result.description == "先手の銀得"

    def test_pawn_exchange_no_change(self):
        """歩を同枚数交換 -> 駒の損得なし。"""
        sfen = "ln1g3nl/1ks1gr3/1ppppsb1p/p4Spp1/9/P1P1P1P2/1P1P1P2P/1BKS3R1/LNG1G2NL w Pp 4"
        result = calculate_material(sfen)
        assert result.description == "駒の損得なし"

    def test_silver_lance_exchange(self):
        """銀香交換。"""
        sfen = "ln1g3n1/1ks1gr3/1ppppsbpp/p4pp2/7P1/P1P1P1P2/1P1P1P2P/1BKS3R1/LNG1G2NL b Ls 1"
        result = calculate_material(sfen)
        assert result.description == "銀と香の交換"

    def test_silver_gain_with_pawn_exchange(self):
        """歩銀交換 -> 銀得（歩は無視）。"""
        sfen = "ln1g3nl/1ks1gr3/1pppp1bpp/p4pp2/9/P1P1PSP2/1P1P1P2P/1BKS3R1/LNG1G2NL b Sp 1"
        result = calculate_material(sfen)
        assert result.description == "先手の銀得"

    def test_bishop_gold_silver_exchange(self):
        """角と金銀の交換。"""
        sfen = "ln1g3nl/1ks2r3/1pppp1bpp/p4pp2/9/P1P1PSP2/1P1P1P2P/2KS3R1/LNG1G2NL b GSbp 1"
        result = calculate_material(sfen)
        assert result.description == "角と金銀の交換"

    def test_bishop_two_silver_exchange(self):
        """角と銀二枚の交換。"""
        sfen = "ln1g3nl/1k2gr3/1pppp1bpp/p2b1pp2/9/P1P1PSP2/1P1P1P2P/2K4R1/LNG1G2NL b 3Sp 1"
        result = calculate_material(sfen)
        assert result.description == "角と銀二枚の交換"

    def test_complex_exchange(self):
        """角桂と銀二枚香の交換。"""
        sfen = "ln1g3n1/1k2gr3/1pppp1bpp/p2b1pp2/9/P1P1PSP2/1P1P1P2P/2K4R1/LNG1G3L b 3SLnp 1"
        result = calculate_material(sfen)
        assert result.description == "角桂と銀二枚香の交換"


class TestMaterialHandPieces:
    """持ち駒情報のテスト。"""

    def test_sente_hand_pieces(self):
        """先手の持ち駒が正しく記録される。"""
        # 先手の持ち駒: G（金）, S（銀）
        sfen = "ln1g3nl/1ks2r3/1pppp1bpp/p4pp2/9/P1P1PSP2/1P1P1P2P/2KS3R1/LNG1G2NL b GSbp 1"
        result = calculate_material(sfen)
        assert result.sente_hand is not None
        assert result.sente_hand.get("金", 0) == 1
        assert result.sente_hand.get("銀", 0) == 1

    def test_gote_hand_pieces(self):
        """後手の持ち駒が正しく記録される。"""
        sfen = "ln1g3nl/1ks1gr3/1ppppsb1p/p4ppp1/4S4/P1P1P1P2/1P1P1P2P/1BKS3R1/LNG1G2NL b p 3"
        result = calculate_material(sfen)
        assert result.gote_hand is not None
        assert result.gote_hand.get("歩", 0) == 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
