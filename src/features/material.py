# -*- coding: utf-8 -*-
"""
駒得計算モジュール

局面から先手・後手の駒点数を計算し、駒得/駒損を判定する。
初期局面からの駒交換状況も記述する。
"""

from dataclasses import dataclass
from typing import Dict, List, Tuple
import cshogi


# ========================================
# 駒の点数定義
# ========================================

PIECE_VALUES = {
    # 生駒
    "歩": 100,
    "香": 300,
    "桂": 400,
    "銀": 500,
    "金": 600,
    "角": 800,
    "飛": 1000,
    # 成駒
    "と": 700,
    "成香": 600,
    "成桂": 600,
    "成銀": 600,
    "馬": 1000,
    "龍": 1200,
}

# 駒の表示順（飛角金銀桂香の順）
PIECE_DISPLAY_ORDER = ["飛", "角", "金", "銀", "桂", "香", "歩"]

# cshogiの駒IDから駒名への変換
CSHOGI_PIECE_TO_NAME = {
    cshogi.PAWN: "歩",
    cshogi.LANCE: "香",
    cshogi.KNIGHT: "桂",
    cshogi.SILVER: "銀",
    cshogi.GOLD: "金",
    cshogi.BISHOP: "角",
    cshogi.ROOK: "飛",
    cshogi.PROM_PAWN: "と",
    cshogi.PROM_LANCE: "成香",
    cshogi.PROM_KNIGHT: "成桂",
    cshogi.PROM_SILVER: "成銀",
    cshogi.PROM_BISHOP: "馬",
    cshogi.PROM_ROOK: "龍",
}

# 成駒から生駒への変換
PROMOTED_TO_BASE = {
    "と": "歩",
    "成香": "香",
    "成桂": "桂",
    "成銀": "銀",
    "馬": "角",
    "龍": "飛",
}

# 持ち駒のインデックス（cshogiのpieces_in_hand順）
HAND_PIECE_ORDER = ["歩", "香", "桂", "銀", "金", "角", "飛"]

# 初期局面の駒数（各陣営が持つ生駒の数）
INITIAL_PIECES = {
    "歩": 9,
    "香": 2,
    "桂": 2,
    "銀": 2,
    "金": 2,
    "角": 1,
    "飛": 1,
}


@dataclass
class MaterialAdvantage:
    """
    駒得情報を格納するデータクラス。

    Attributes:
        sente_score: 先手の駒点数合計（玉を除く）
        gote_score: 後手の駒点数合計（玉を除く）
        advantage: 先手視点の駒得（正=先手有利、負=後手有利）
        description: 日本語での説明（例: "銀香交換"）
        sente_hand: 先手の持ち駒
        gote_hand: 後手の持ち駒
    """
    sente_score: int
    gote_score: int
    advantage: int
    description: str
    sente_hand: Dict[str, int] = None
    gote_hand: Dict[str, int] = None


def _count_pieces(board: cshogi.Board) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    盤上と持ち駒を合わせた各陣営の駒数をカウントする。
    成駒は生駒としてカウントする。

    Args:
        board: cshogiのBoardオブジェクト

    Returns:
        (先手の駒数, 後手の駒数) の辞書タプル
    """
    sente_count = {p: 0 for p in HAND_PIECE_ORDER}
    gote_count = {p: 0 for p in HAND_PIECE_ORDER}

    # 盤上の駒をカウント
    for sq in range(81):
        piece = board.piece(sq)
        if piece == cshogi.NONE:
            continue

        piece_type = piece & 0x0F
        is_white = (piece & 0x10) != 0

        if piece_type == cshogi.KING:
            continue

        piece_name = CSHOGI_PIECE_TO_NAME.get(piece_type)
        if piece_name is None:
            continue

        # 成駒は生駒に変換
        base_name = PROMOTED_TO_BASE.get(piece_name, piece_name)
        
        if is_white:
            gote_count[base_name] = gote_count.get(base_name, 0) + 1
        else:
            sente_count[base_name] = sente_count.get(base_name, 0) + 1

    # 持ち駒をカウント
    hands = board.pieces_in_hand
    sente_hand, gote_hand = hands

    for i, piece_name in enumerate(HAND_PIECE_ORDER):
        sente_count[piece_name] += sente_hand[i]
        gote_count[piece_name] += gote_hand[i]

    return sente_count, gote_count


def _generate_exchange_description(
    sente_count: Dict[str, int],
    gote_count: Dict[str, int],
    ref_sente_count: Dict[str, int] = None,
    ref_gote_count: Dict[str, int] = None
) -> str:
    """
    駒交換のdescriptionを生成する。

    Args:
        sente_count: 現在の先手の駒数
        gote_count: 現在の後手の駒数
        ref_sente_count: 比較元の先手の駒数（Noneなら初期局面）
        ref_gote_count: 比較元の後手の駒数（Noneなら初期局面）

    Returns:
        駒交換の説明文
    """
    # 比較元がNoneなら初期局面を使用
    if ref_sente_count is None:
        ref_sente_count = INITIAL_PIECES.copy()
    if ref_gote_count is None:
        ref_gote_count = INITIAL_PIECES.copy()

    # 先手が得た駒（後手から取った駒）= 現在の先手 - 比較元の先手
    # 後手が得た駒（先手から取った駒）= 現在の後手 - 比較元の後手
    sente_gained = {}  # 先手が得た駒
    gote_gained = {}   # 後手が得た駒

    for piece in HAND_PIECE_ORDER:
        sente_diff = sente_count.get(piece, 0) - ref_sente_count.get(piece, 0)
        gote_diff = gote_count.get(piece, 0) - ref_gote_count.get(piece, 0)

        if sente_diff > 0:
            sente_gained[piece] = sente_diff
        if gote_diff > 0:
            gote_gained[piece] = gote_diff

    # 歩以外の交換があるか確認
    sente_gained_non_pawn = {k: v for k, v in sente_gained.items() if k != "歩"}
    gote_gained_non_pawn = {k: v for k, v in gote_gained.items() if k != "歩"}

    # 駒の損得なし
    if not sente_gained and not gote_gained:
        return "駒の損得なし"

    # 歩以外の交換がある場合、歩は無視
    if sente_gained_non_pawn or gote_gained_non_pawn:
        sente_gained = sente_gained_non_pawn
        gote_gained = gote_gained_non_pawn

    # 歩のみの交換
    if not sente_gained and not gote_gained:
        return "駒の損得なし"

    # 一方的な得/損
    if sente_gained and not gote_gained:
        pieces_str = _format_pieces(sente_gained)
        pawn_count = sente_gained.get("歩", 0)
        if "歩" in sente_gained and len(sente_gained) == 1:
            # 歩のみ
            if pawn_count == 1:
                return "先手の歩得"
            else:
                return f"先手の{_num_to_japanese(pawn_count)}歩得"
        return f"先手の{pieces_str}得"
    
    if gote_gained and not sente_gained:
        pieces_str = _format_pieces(gote_gained)
        pawn_count = gote_gained.get("歩", 0)
        if "歩" in gote_gained and len(gote_gained) == 1:
            # 歩のみ
            if pawn_count == 1:
                return "先手の歩損"
            else:
                return f"先手の{_num_to_japanese(pawn_count)}歩損"
        return f"先手の{pieces_str}損"

    # 両者が駒を得ている（交換）
    # 表記: 「先手が失った駒と後手が失った駒の交換」
    # = 「後手が得た駒と先手が得た駒の交換」
    # ユーザー例: 先手の銀と後手の香が交換 -> 銀香交換
    gote_str = _format_pieces(gote_gained)  # 先手が失った駒
    sente_str = _format_pieces(sente_gained)  # 後手が失った駒
    
    return f"{gote_str}と{sente_str}の交換"


def _format_pieces(pieces: Dict[str, int]) -> str:
    """
    駒の辞書をフォーマットする。
    順序は飛角金銀桂香の順。

    Args:
        pieces: 駒種 -> 枚数 の辞書

    Returns:
        フォーマットされた文字列（例: "角桂", "銀二枚"）
    """
    result = []
    for piece in PIECE_DISPLAY_ORDER:
        count = pieces.get(piece, 0)
        if count == 0:
            continue
        if count == 1:
            result.append(piece)
        else:
            result.append(f"{piece}{_num_to_japanese(count)}枚")
    return "".join(result)


def _num_to_japanese(n: int) -> str:
    """数字を漢数字に変換する。"""
    japanese = {1: "一", 2: "二", 3: "三", 4: "四", 5: "五", 
                6: "六", 7: "七", 8: "八", 9: "九"}
    return japanese.get(n, str(n))


def calculate_material(sfen: str) -> MaterialAdvantage:
    """
    SFEN文字列から駒得を計算する。

    Args:
        sfen: 局面を表すSFEN文字列

    Returns:
        MaterialAdvantage: 駒得情報
    """
    board = cshogi.Board(sfen)
    return calculate_material_from_board(board)


def calculate_material_from_board(board: cshogi.Board) -> MaterialAdvantage:
    """
    cshogiのBoardオブジェクトから駒得を計算する。

    玉は点数計算から除外する。

    Args:
        board: cshogiのBoardオブジェクト

    Returns:
        MaterialAdvantage: 駒得情報
    """
    sente_score = 0
    gote_score = 0

    # 盤上の駒を計算
    for sq in range(81):
        piece = board.piece(sq)
        if piece == cshogi.NONE:
            continue

        piece_type = piece & 0x0F
        is_white = (piece & 0x10) != 0

        if piece_type == cshogi.KING:
            continue

        piece_name = CSHOGI_PIECE_TO_NAME.get(piece_type)
        if piece_name is None:
            continue

        value = PIECE_VALUES.get(piece_name, 0)
        if is_white:
            gote_score += value
        else:
            sente_score += value

    # 持ち駒を計算
    hands = board.pieces_in_hand
    sente_hand_raw, gote_hand_raw = hands

    sente_hand = {}
    gote_hand = {}
    
    for i, piece_name in enumerate(HAND_PIECE_ORDER):
        value = PIECE_VALUES.get(piece_name, 0)
        sente_score += sente_hand_raw[i] * value
        gote_score += gote_hand_raw[i] * value
        
        sente_hand[piece_name] = sente_hand_raw[i]
        gote_hand[piece_name] = gote_hand_raw[i]

    advantage = sente_score - gote_score

    # 駒交換のdescriptionを生成
    sente_count, gote_count = _count_pieces(board)
    description = _generate_exchange_description(sente_count, gote_count)

    return MaterialAdvantage(
        sente_score=sente_score,
        gote_score=gote_score,
        advantage=advantage,
        description=description,
        sente_hand=sente_hand,
        gote_hand=gote_hand,
    )


def generate_material_change_description(
    before_sente_count: Dict[str, int],
    before_gote_count: Dict[str, int],
    after_sente_count: Dict[str, int],
    after_gote_count: Dict[str, int]
) -> str:
    """
    2つの局面間の駒交換descriptionを生成する。

    Args:
        before_sente_count: before局面の先手の駒数
        before_gote_count: before局面の後手の駒数
        after_sente_count: after局面の先手の駒数
        after_gote_count: after局面の後手の駒数

    Returns:
        駒交換の説明文
    """
    return _generate_exchange_description(
        after_sente_count,
        after_gote_count,
        before_sente_count,
        before_gote_count
    )


def get_piece_counts_from_board(board: cshogi.Board) -> Tuple[Dict[str, int], Dict[str, int]]:
    """
    Boardオブジェクトから駒数を取得する（外部から利用可能）。

    Args:
        board: cshogiのBoardオブジェクト

    Returns:
        (先手の駒数, 後手の駒数) の辞書タプル
    """
    return _count_pieces(board)


if __name__ == "__main__":
    # テスト用
    test_cases = [
        # (SFEN, 期待されるdescription)
        ("ln1g3nl/1ks1gr3/1ppppsb1p/p4ppp1/4S4/P1P1P1P2/1P1P1P2P/1BKS3R1/LNG1G2NL b p 3", "先手の歩損"),
        ("ln1g3nl/1ks1gr3/1ppppsb1p/p4p1p1/4S1p2/P1P1P4/1P1P1P2P/1BKS3R1/LNG1G2NL b 2p 5", "先手の二歩損"),
        ("ln1g3nl/1ks1gr3/1pppp1bpp/p3SppP1/9/P1P1P1P2/1P1P1P2P/1BKS3R1/LNG1G2NL w S 4", "先手の銀得"),
        ("ln1g3nl/1ks1gr3/1ppppsb1p/p4Spp1/9/P1P1P1P2/1P1P1P2P/1BKS3R1/LNG1G2NL w Pp 4", "駒の損得なし"),
        ("ln1g3n1/1ks1gr3/1ppppsbpp/p4pp2/7P1/P1P1P1P2/1P1P1P2P/1BKS3R1/LNG1G2NL b Ls 1", "銀と香の交換"),
        ("ln1g3nl/1ks1gr3/1pppp1bpp/p4pp2/9/P1P1PSP2/1P1P1P2P/1BKS3R1/LNG1G2NL b Sp 1", "先手の銀得"),
        ("ln1g3nl/1ks2r3/1pppp1bpp/p4pp2/9/P1P1PSP2/1P1P1P2P/2KS3R1/LNG1G2NL b GSbp 1", "角と金銀の交換"),
        ("ln1g3nl/1k2gr3/1pppp1bpp/p2b1pp2/9/P1P1PSP2/1P1P1P2P/2K4R1/LNG1G2NL b 3Sp 1", "角と銀三枚の交換"),
        ("ln1g3n1/1k2gr3/1pppp1bpp/p2b1pp2/9/P1P1PSP2/1P1P1P2P/2K4R1/LNG1G3L b 3SLnp 1", "角桂と香銀三枚の交換"),
    ]

    print("テスト実行:")
    for sfen, expected in test_cases:
        result = calculate_material(sfen)
        status = "✓" if result.description == expected else "✗"
        print(f"{status} 期待: '{expected}', 実際: '{result.description}'")
