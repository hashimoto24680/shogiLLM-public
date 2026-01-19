# -*- coding: utf-8 -*-
"""
KIF/USI変換に関する補助関数
"""

from .kif_mappings import PIECE_ID_TO_NAME


def piece_name_from_board(board, from_usi: str) -> str:
    """
    cshogi.Boardから移動元の駒名を取得する。

    Args:
        board: cshogi.Board
        from_usi: 移動元USI座標（例: "7g"）

    Returns:
        駒名（取得できない場合は空文字）
    """
    if board is None:
        return ""

    file_idx = int(from_usi[0]) - 1
    rank_idx = ord(from_usi[1].lower()) - ord('a')
    from_sq = file_idx * 9 + rank_idx
    piece = board.piece(from_sq)
    if not piece:
        return ""

    if piece >= 16:
        piece_id = (piece - 16) % 16
        if piece >= 25:
            piece_id = piece - 16
    else:
        piece_id = piece

    return PIECE_ID_TO_NAME.get(piece_id, "")
