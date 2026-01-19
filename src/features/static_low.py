# -*- coding: utf-8 -*-
"""
低次元静的特徴抽出モジュール

cshogiを使用して81マスの情報と持ち駒を抽出する。

座標系の詳細は docs/utils/coordinate_system.md を参照。
"""

from __future__ import annotations

import cshogi

from src.features.models import BasePiece, HandPieces, PieceInfo, SquareInfo
from src.utils.attacks import get_piece_attacks
from src.utils.coordinates import index_to_japanese


# ========================================
# 定数定義
# ========================================

# cshogiの駒種から日本語名への変換
PIECE_TYPE_TO_JAPANESE = {
    cshogi.PAWN: "歩",
    cshogi.LANCE: "香",
    cshogi.KNIGHT: "桂",
    cshogi.SILVER: "銀",
    cshogi.GOLD: "金",
    cshogi.BISHOP: "角",
    cshogi.ROOK: "飛",
    cshogi.KING: "玉",
    cshogi.PROM_PAWN: "と",
    cshogi.PROM_LANCE: "成香",
    cshogi.PROM_KNIGHT: "成桂",
    cshogi.PROM_SILVER: "成銀",
    cshogi.PROM_BISHOP: "馬",
    cshogi.PROM_ROOK: "龍",
}

# 持ち駒の駒種（cshogiのpieces_in_hand順）
HAND_PIECE_TYPES = ["歩", "香", "桂", "銀", "金", "角", "飛"]

# 8方向の定義（先手視点）
# file方向: 正=右（9筋方向）、負=左（1筋方向）
# rank方向: 正=下（九段方向）、負=上（一段方向）
DIRECTION_NAMES = {
    (-1, -1): "左上",
    (0, -1): "上",
    (1, -1): "右上",
    (-1, 0): "左",
    (1, 0): "右",
    (-1, 1): "左下",
    (0, 1): "下",
    (1, 1): "右下",
}


# ========================================
# 公開関数
# ========================================


def square_to_japanese(sq: int) -> str:
    """マス番号を日本語座標に変換する。

    Args:
        sq: マスインデックス（0-80）

    Returns:
        日本語座標（例: "5五"）

    Examples:
        >>> square_to_japanese(0)
        '1一'
        >>> square_to_japanese(40)
        '5五'
        >>> square_to_japanese(80)
        '9九'
    """
    return index_to_japanese(sq)


def get_adjacent_squares(sq: int) -> dict[str, str | None]:
    """8方向の隣接マスを取得する。

    先手視点での8方向（上下左右、四隅）の隣接マスを返す。
    盤外の場合はNoneを返す。

    Args:
        sq: マスインデックス（0-80）

    Returns:
        8方向の隣接マス辞書（例: {"上": "5四", "下": "5六", ...}）
        盤外の方向はNone

    Examples:
        >>> adj = get_adjacent_squares(40)  # 5五
        >>> adj["上"]
        '5四'
        >>> adj["下"]
        '5六'
    """
    file = sq // 9
    rank = sq % 9

    adjacent = {}
    for (df, dr), name in DIRECTION_NAMES.items():
        new_file = file + df
        new_rank = rank + dr

        if 0 <= new_file <= 8 and 0 <= new_rank <= 8:
            new_sq = new_file * 9 + new_rank
            adjacent[name] = index_to_japanese(new_sq)
        else:
            adjacent[name] = None

    return adjacent


def extract_square_info(board: cshogi.Board, sq: int) -> SquareInfo:
    """1マスの情報を抽出する。

    指定されたマスの駒情報、利き情報、隣接マス情報を抽出する。

    Args:
        board: cshogiのBoardオブジェクト
        sq: マスインデックス（0-80）

    Returns:
        SquareInfo: マスの情報
    """
    square_jp = square_to_japanese(sq)
    adjacent = get_adjacent_squares(sq)

    # 駒の情報を取得
    piece_code = board.piece(sq)
    piece_info = None

    if piece_code != cshogi.NONE:
        # 駒種と手番を取得
        piece_type = piece_code & 0x0F  # 下位4ビットで駒種
        is_white = (piece_code & 0x10) != 0  # 5ビット目で後手判定

        piece_name = PIECE_TYPE_TO_JAPANESE.get(piece_type, "不明")
        color = "後手" if is_white else "先手"
        piece_color = cshogi.WHITE if is_white else cshogi.BLACK

        # 利きの計算
        attack_indices = get_piece_attacks(board, sq, piece_type, piece_color)
        attack_squares = [index_to_japanese(idx) for idx in attack_indices]

        # 移動可能マス（自駒がいないマス）
        movable_squares = []
        for idx in attack_indices:
            target_piece = board.piece(idx)
            if target_piece == cshogi.NONE:
                # 空のマスには移動可能
                movable_squares.append(index_to_japanese(idx))
            else:
                # 敵駒のマスには移動可能（取れる）
                target_is_white = (target_piece & 0x10) != 0
                if is_white != target_is_white:
                    movable_squares.append(index_to_japanese(idx))

        piece_info = PieceInfo(
            piece_type=piece_name,
            color=color,
            square=square_jp,
            attack_squares=attack_squares,
            movable_squares=movable_squares,
            activity=0,  # 後でdlshogiで計算
        )

    # 利き情報の計算
    direct_attackers = _get_attackers(board, sq, direct=True)
    indirect_attackers = _get_attackers(board, sq, direct=False)
    attack_balance = _calculate_attack_balance(board, sq)

    return SquareInfo(
        square=square_jp,
        piece=piece_info,
        adjacent=adjacent,
        direct_attackers=direct_attackers,
        indirect_attackers=indirect_attackers,
        attack_balance=attack_balance,
    )


def extract_all_squares(board: cshogi.Board) -> list[SquareInfo]:
    """81マス全ての情報を抽出する。

    Args:
        board: cshogiのBoardオブジェクト

    Returns:
        81マス分のSquareInfoリスト
    """
    return [extract_square_info(board, sq) for sq in range(81)]


def extract_hand_pieces(board: cshogi.Board) -> list[HandPieces]:
    """先手・後手の持ち駒を抽出する。

    Args:
        board: cshogiのBoardオブジェクト

    Returns:
        [先手の持ち駒, 後手の持ち駒] のリスト
    """
    hands = board.pieces_in_hand
    sente_hand, gote_hand = hands

    result = []
    for color, hand_array in [("先手", sente_hand), ("後手", gote_hand)]:
        pieces = {}
        for i, piece_name in enumerate(HAND_PIECE_TYPES):
            if hand_array[i] > 0:
                pieces[piece_name] = hand_array[i]
            else:
                pieces[piece_name] = 0
        result.append(HandPieces(color=color, pieces=pieces))

    return result


# ========================================
# 内部関数
# ========================================


def _get_attackers(
    board: cshogi.Board, target_sq: int, direct: bool = True
) -> list[BasePiece]:
    """指定マスに利きを持つ駒のリストを取得する。

    Args:
        board: cshogiのBoardオブジェクト
        target_sq: 対象マス（0-80）
        direct: Trueなら直接利き、Falseなら間接利き

    Returns:
        利きを持つ駒のBasePieceリスト
    
    Note:
        間接利きとは：
        ①飛び駒（香・角・飛・馬・龍）が間に駒を挟んでいる
        ②間の駒が味方の駒
        ③間の駒も対象マスに利きがある
    """
    attackers = []

    for sq in range(81):
        piece_code = board.piece(sq)
        if piece_code == cshogi.NONE:
            continue

        piece_type = piece_code & 0x0F
        is_white = (piece_code & 0x10) != 0
        piece_color = cshogi.WHITE if is_white else cshogi.BLACK

        attacks = get_piece_attacks(board, sq, piece_type, piece_color)

        if direct:
            # 直接利き
            if target_sq in attacks:
                attackers.append(
                    BasePiece(
                        piece_type=PIECE_TYPE_TO_JAPANESE.get(piece_type, "不明"),
                        color="後手" if is_white else "先手",
                        square=index_to_japanese(sq),
                    )
                )
        else:
            # 間接利き（飛び駒が間に味方駒を挟んでいて、その味方駒が対象に利きがある）
            if piece_type not in [
                cshogi.LANCE,
                cshogi.BISHOP,
                cshogi.ROOK,
                cshogi.PROM_BISHOP,
                cshogi.PROM_ROOK,
            ]:
                continue
            
            # 対象マスへの直線上を調べる
            blocking_piece = _find_blocking_piece(board, sq, target_sq, piece_type)
            if blocking_piece is None:
                continue
            
            blocking_sq, blocking_code = blocking_piece
            blocking_is_white = (blocking_code & 0x10) != 0
            
            # ②間の駒が味方かチェック
            if is_white != blocking_is_white:
                continue  # 敵駒なら間接利きではない
            
            # ③間の駒が対象マスに利きがあるかチェック
            blocking_type = blocking_code & 0x0F
            blocking_color = cshogi.WHITE if blocking_is_white else cshogi.BLACK
            blocking_attacks = get_piece_attacks(board, blocking_sq, blocking_type, blocking_color)
            
            if target_sq in blocking_attacks:
                # 間接利き成立
                attackers.append(
                    BasePiece(
                        piece_type=PIECE_TYPE_TO_JAPANESE.get(piece_type, "不明"),
                        color="後手" if is_white else "先手",
                        square=index_to_japanese(sq),
                    )
                )

    return attackers


def _find_blocking_piece(
    board: cshogi.Board, from_sq: int, to_sq: int, piece_type: int
) -> tuple[int, int] | None:
    """飛び駒の直線上で最初にブロックしている駒を見つける。
    
    Args:
        board: cshogiのBoardオブジェクト
        from_sq: 飛び駒のマス
        to_sq: 対象マス
        piece_type: 飛び駒の駒種
    
    Returns:
        (駒のマス, 駒コード) のタプル、または None
    """
    from_file = from_sq // 9
    from_rank = from_sq % 9
    to_file = to_sq // 9
    to_rank = to_sq % 9
    
    # 方向を計算
    df = 0 if to_file == from_file else (1 if to_file > from_file else -1)
    dr = 0 if to_rank == from_rank else (1 if to_rank > from_rank else -1)
    
    # 直線上かチェック
    if df == 0 and dr == 0:
        return None
    
    # 駒種に応じた方向チェック
    if piece_type == cshogi.LANCE:
        # 香は前方のみ（先手なら上方向、後手なら下方向）
        # ここでは単純に縦方向のみチェック
        if df != 0:
            return None
    elif piece_type in [cshogi.BISHOP, cshogi.PROM_BISHOP]:
        # 角は斜め方向のみ
        if df == 0 or dr == 0:
            return None
        if abs(to_file - from_file) != abs(to_rank - from_rank):
            return None
    elif piece_type in [cshogi.ROOK, cshogi.PROM_ROOK]:
        # 飛は縦横のみ
        if df != 0 and dr != 0:
            return None
    
    # 直線上を走査
    current_file = from_file + df
    current_rank = from_rank + dr
    
    while 0 <= current_file <= 8 and 0 <= current_rank <= 8:
        current_sq = current_file * 9 + current_rank
        
        if current_sq == to_sq:
            return None  # 対象マスに到達（間に駒なし）
        
        piece = board.piece(current_sq)
        if piece != cshogi.NONE:
            return (current_sq, piece)  # ブロックしている駒を発見
        
        current_file += df
        current_rank += dr
    
    return None


def _calculate_attack_balance(board: cshogi.Board, target_sq: int) -> int:
    """指定マスの利きバランスを計算する。

    直接利き + 間接利き の先手数 - 後手数 を返す。

    Args:
        board: cshogiのBoardオブジェクト
        target_sq: 対象マス（0-80）

    Returns:
        利きバランス（正=先手有利、負=後手有利）
    """
    # 直接利きと間接利きを取得
    direct_attackers = _get_attackers(board, target_sq, direct=True)
    indirect_attackers = _get_attackers(board, target_sq, direct=False)
    
    sente_attacks = 0
    gote_attacks = 0
    
    for attacker in direct_attackers + indirect_attackers:
        if attacker.color == "先手":
            sente_attacks += 1
        else:
            gote_attacks += 1

    return sente_attacks - gote_attacks

