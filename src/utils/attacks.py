# -*- coding: utf-8 -*-
"""
駒の利き計算ユーティリティ

指定した駒がどのマスに利いているかを計算する関数を提供する。
cshogiには直接attacksFromがエクスポートされていないため、
各駒種の移動パターンから計算する。
"""

from typing import List

import cshogi


def get_piece_attacks(
    board: cshogi.Board,
    square: int,
    piece_type: int,
    piece_color: int
) -> List[int]:
    """
    指定した駒の利き先マスのリストを取得する。

    Args:
        board: cshogiのBoardオブジェクト
        square: 駒のいるマス（0-80）
        piece_type: 駒種（1-14）
        piece_color: 駒の色（BLACK=0, WHITE=1）

    Returns:
        利き先マスのリスト（マスインデックス0-80）

    Note:
        駒種の対応:
        歩(1), 香(2), 桂(3), 銀(4), 角(5), 飛(6), 金(7), 王(8)
        と(9), 成香(10), 成桂(11), 成銀(12), 馬(13), 龍(14)
    """
    attacks = []
    
    file_from = square // 9
    rank_from = square % 9

    if piece_type == cshogi.PAWN:  # 歩
        # 前方1マス
        if piece_color == cshogi.BLACK:
            attacks = _add_if_valid(attacks, file_from, rank_from - 1)
        else:
            attacks = _add_if_valid(attacks, file_from, rank_from + 1)
            
    elif piece_type == cshogi.LANCE:  # 香
        # 前方に直進
        dr = -1 if piece_color == cshogi.BLACK else 1
        r = rank_from + dr
        while 0 <= r <= 8:
            sq = file_from * 9 + r
            attacks.append(sq)
            # 駒があれば止まる
            if board.piece(sq) != cshogi.NONE:
                break
            r += dr
            
    elif piece_type == cshogi.KNIGHT:  # 桂
        if piece_color == cshogi.BLACK:
            attacks = _add_if_valid(attacks, file_from - 1, rank_from - 2)
            attacks = _add_if_valid(attacks, file_from + 1, rank_from - 2)
        else:
            attacks = _add_if_valid(attacks, file_from - 1, rank_from + 2)
            attacks = _add_if_valid(attacks, file_from + 1, rank_from + 2)
            
    elif piece_type == cshogi.SILVER:  # 銀
        if piece_color == cshogi.BLACK:
            directions = [(-1, -1), (0, -1), (1, -1), (-1, 1), (1, 1)]
        else:
            directions = [(-1, 1), (0, 1), (1, 1), (-1, -1), (1, -1)]
        for df, dr in directions:
            attacks = _add_if_valid(attacks, file_from + df, rank_from + dr)
            
    elif piece_type == cshogi.GOLD or piece_type in [
        cshogi.PROM_PAWN, cshogi.PROM_LANCE, cshogi.PROM_KNIGHT, cshogi.PROM_SILVER
    ]:  # 金・成駒
        if piece_color == cshogi.BLACK:
            directions = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (0, 1)]
        else:
            directions = [(-1, 1), (0, 1), (1, 1), (-1, 0), (1, 0), (0, -1)]
        for df, dr in directions:
            attacks = _add_if_valid(attacks, file_from + df, rank_from + dr)
            
    elif piece_type == cshogi.KING:  # 王
        for df in [-1, 0, 1]:
            for dr in [-1, 0, 1]:
                if df == 0 and dr == 0:
                    continue
                attacks = _add_if_valid(attacks, file_from + df, rank_from + dr)
                
    elif piece_type == cshogi.BISHOP:  # 角
        attacks = _get_sliding_attacks(
            board, file_from, rank_from,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        )
        
    elif piece_type == cshogi.ROOK:  # 飛
        attacks = _get_sliding_attacks(
            board, file_from, rank_from,
            [(-1, 0), (1, 0), (0, -1), (0, 1)]
        )
        
    elif piece_type == cshogi.PROM_BISHOP:  # 馬
        attacks = _get_sliding_attacks(
            board, file_from, rank_from,
            [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        )
        # 十字方向1マス追加
        for df, dr in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            attacks = _add_if_valid(attacks, file_from + df, rank_from + dr)
            
    elif piece_type == cshogi.PROM_ROOK:  # 龍
        attacks = _get_sliding_attacks(
            board, file_from, rank_from,
            [(-1, 0), (1, 0), (0, -1), (0, 1)]
        )
        # 斜め方向1マス追加
        for df, dr in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
            attacks = _add_if_valid(attacks, file_from + df, rank_from + dr)

    return attacks


def _add_if_valid(attacks: List[int], file: int, rank: int) -> List[int]:
    """
    マスが盤内なら利きリストに追加する。

    Args:
        attacks: 利きリスト
        file: 筋（0-8）
        rank: 段（0-8）

    Returns:
        更新された利きリスト
    """
    if 0 <= file <= 8 and 0 <= rank <= 8:
        attacks.append(file * 9 + rank)
    return attacks


def _get_sliding_attacks(
    board: cshogi.Board,
    file_from: int,
    rank_from: int,
    directions: List[tuple]
) -> List[int]:
    """
    飛び駒（香・角・飛・馬・龍）の利きを取得する。

    Args:
        board: cshogiのBoardオブジェクト
        file_from: 駒の筋（0-8）
        rank_from: 駒の段（0-8）
        directions: 探索方向のリスト（(df, dr)のタプル）

    Returns:
        利き先マスのリスト
    """
    attacks = []
    for df, dr in directions:
        f, r = file_from + df, rank_from + dr
        while 0 <= f <= 8 and 0 <= r <= 8:
            sq = f * 9 + r
            attacks.append(sq)
            if board.piece(sq) != cshogi.NONE:
                break
            f += df
            r += dr
    return attacks
