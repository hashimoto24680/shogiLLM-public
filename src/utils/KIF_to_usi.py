# -*- coding: utf-8 -*-
"""
KIF形式の指し手をUSI形式に変換するユーティリティ

KIF記法の指し手（例: '７六歩(77)', '同歩', '５五角打'）を
USI形式（例: '7g7f', '7f7e', 'B*5e'）に変換する。
"""

import re

from .kif_helpers import piece_name_from_board
from .kif_mappings import (
    KANJI_TO_NUM,
    NUM_TO_KANJI,
    NUM_TO_ZENKAKU,
    PIECE_TO_USI,
    RANK_TO_USI,
    USI_RANK_TO_NUM,
    USI_TO_PIECE,
    ZENKAKU_TO_HANKAKU,
)


def kif_move_to_usi(kif_move: str, last_to_square: str = None) -> tuple[str, str]:
    """
    KIFの指し手をUSI形式に変換する。
    
    Args:
        kif_move: KIF形式の指し手（例: '７六歩(77)', '同歩', '５五角打'）
        last_to_square: 直前の指し手の移動先（「同」指し手の処理に使用）
    
    Returns:
        (usi_move, to_square): USI形式の指し手と移動先マス
    
    Raises:
        ValueError: 無効な指し手フォーマットの場合
    
    Examples:
        >>> kif_move_to_usi('７六歩(77)')
        ('7g7f', '7f')
        >>> kif_move_to_usi('同歩(76)', '7f')
        ('7f7e', '7e')  # 仮の例
        >>> kif_move_to_usi('５五角打')
        ('B*5e', '5e')
    """
    # 空白や不要な文字を除去
    kif_move = kif_move.strip()
    
    # 「同」の処理
    if kif_move.startswith("同"):
        if not last_to_square:
            raise ValueError("「同」指し手には前の指し手の情報が必要です。")
        
        # 「同歩(76)」形式の場合、元の位置を抽出
        from_match = re.search(r'\((\d)(\d)\)', kif_move)
        if from_match:
            from_file = from_match.group(1)
            from_rank = int(from_match.group(2))
            from_square = f"{from_file}{RANK_TO_USI[from_rank]}"
            
            # 駒種を抽出（「同」の後から「(」の前まで）
            # 例: 「同　成桂(47)」-> 「成桂」, 「同　歩(76)」-> 「歩」
            piece_match = re.search(r'^同[\s　]*([^(]+)', kif_move)
            piece_part = piece_match.group(1).strip() if piece_match else ""
            
            # 成りの処理:
            # - 成香/成桂/成銀/と/馬/竜/龍 は既に成っている駒なので成らない
            # - 動作として「成」がある場合のみ成る（例: 「同　角成(22)」）
            already_promoted_pieces = ('成香', '成桂', '成銀', 'と', '馬', '竜', '龍')
            is_already_promoted = any(piece_part.startswith(p) for p in already_promoted_pieces)
            
            # 末尾が「成」で終わる場合のみ成りと判定
            is_nari_action = piece_part.endswith('成') and not is_already_promoted
            
            if is_nari_action and "不成" not in kif_move:
                usi_move = f"{from_square}{last_to_square}+"
            else:
                usi_move = f"{from_square}{last_to_square}"
            
            return usi_move, last_to_square
        else:
            # 元の位置情報がない場合はエラー
            raise ValueError(f"「同」指し手に元の位置情報がありません: {kif_move}")
    
    # 「打」の処理（持ち駒を打つ場合）
    drop_match = re.match(
        r'^([１２３４５６７８９])([一二三四五六七八九])([歩香桂銀金角飛])打$',
        kif_move
    )
    if drop_match:
        to_file = ZENKAKU_TO_HANKAKU[drop_match.group(1)]
        to_rank = KANJI_TO_NUM[drop_match.group(2)]
        piece = drop_match.group(3)
        
        usi_piece = PIECE_TO_USI.get(piece)
        if not usi_piece:
            raise ValueError(f"不明な駒種類: {piece}")
        
        to_square = f"{to_file}{RANK_TO_USI[to_rank]}"
        usi_move = f"{usi_piece}*{to_square}"
        
        return usi_move, to_square
    
    # 通常の指し手の処理（成り/不成りを含む）
    # 例: '７六歩(77)', '３三角成(22)', '４四銀不成(53)'
    normal_match = re.match(
        r'^([１２３４５６７８９])([一二三四五六七八九])'
        r'([歩香桂銀金角飛王玉と馬竜龍成]*)(?:不成|成)?'
        r'\((\d)(\d)\)$',
        kif_move
    )
    if normal_match:
        # 到達地点
        to_file = ZENKAKU_TO_HANKAKU[normal_match.group(1)]
        to_rank = KANJI_TO_NUM[normal_match.group(2)]
        to_rank_usi = RANK_TO_USI[to_rank]
        to_square = f"{to_file}{to_rank_usi}"
        
        # 元の位置
        from_file = normal_match.group(4)
        from_rank = int(normal_match.group(5))
        from_square = f"{from_file}{RANK_TO_USI[from_rank]}"
        
        # 駒種（成香、成桂、成銀など既に成っている駒かどうか）
        piece_part = normal_match.group(3)
        
        # 成りの処理:
        # - 「不成」の場合は成らない
        # - 駒種が成香/成桂/成銀/と/馬/竜/龍の場合は既に成っているので成らない
        # - 指し手の括弧より前の部分が「成」で終わる場合のみ成りと判定
        #   例: '３三角成(22)' は成りあり、'８九成香(99)' は成りなし
        already_promoted_pieces = ('成香', '成桂', '成銀', 'と', '馬', '竜', '龍')
        is_already_promoted = piece_part in already_promoted_pieces
        
        # 成りの判定: 括弧の前が「成」で終わり、かつ既に成っている駒でない場合
        move_part = kif_move.split('(')[0]  # 例: '３三角成' or '８九成香'
        is_nari_action = move_part.endswith('成') and not is_already_promoted
        
        if is_nari_action and "不成" not in kif_move:
            usi_move = f"{from_square}{to_square}+"
        else:
            usi_move = f"{from_square}{to_square}"
        
        return usi_move, to_square
    
    raise ValueError(f"無効な指し手フォーマット: {kif_move}")


def parse_kif_from_text(kif_text: str) -> list[str]:
    """
    KIFファイルのテキスト内容から指し手を抽出し、USI形式のリストを返す。
    
    Args:
        kif_text: KIFファイルの内容
    
    Returns:
        USI形式の指し手リスト
    """
    moves = []
    last_to_square = None
    lines = kif_text.splitlines()
    move_section = False
    
    for line in lines:
        line = line.strip()
        
        # 指し手セクションの開始判定
        if line.startswith('手数----指手'):
            move_section = True
            continue
        
        if move_section:
            # 終局判定
            if line.startswith(('投了', '持将棋', '千日手')):
                break
            
            # 指し手行の解析
            move_parts = line.split()
            if len(move_parts) >= 2:
                kif_move = move_parts[1]
                try:
                    usi_move, to_square = kif_move_to_usi(kif_move, last_to_square)
                    moves.append(usi_move)
                    last_to_square = to_square
                except ValueError as e:
                    print(f"警告: {e}")
    
    return moves


def parse_kif(file_path: str) -> list[str]:
    """
    KIFファイルからテキストを読み込んでUSI形式の指し手リストを返す。
    
    Args:
        file_path: KIFファイルのパス
    
    Returns:
        USI形式の指し手リスト
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        kif_text = f.read()
    return parse_kif_from_text(kif_text)


def usi_move_to_kif(usi_move: str, board=None, prev_to_square: str = None) -> str:
    """
    USI形式の指し手をKIF形式に変換する。
    
    Args:
        usi_move: USI形式の指し手（例: '7g7f', 'B*5e', '7f7e+'）
        board: cshogi.Board オブジェクト（駒種類の取得と手番判定に使用）
        prev_to_square: 前回の指し手の移動先（例: '7f'）。
                        同じマスへの移動時に「同」表記を使用。
    
    Returns:
        KIF形式の指し手（例: '▲７六歩', '△５五角打', '▲同歩'）
        
    Examples:
        >>> import cshogi
        >>> board = cshogi.Board()
        >>> usi_move_to_kif('7g7f', board)
        '▲７六歩'
        >>> board.push_usi('7g7f')
        >>> usi_move_to_kif('3c3d', board, '7f')  # 別のマスへの移動
        '△３四歩'
        >>> usi_move_to_kif('7a7f', board, '7f')  # 同じマスへの移動（仮定的な例）
        '△同飛'
    """
    import cshogi
    
    # 手番記号
    turn_mark = ""
    if board is not None:
        turn_mark = "▲" if board.turn == cshogi.BLACK else "△"
    
    # 打ち駒の場合（例: 'B*5e'）
    if '*' in usi_move:
        piece_usi = usi_move[0]
        to_file = int(usi_move[2])
        to_rank = USI_RANK_TO_NUM[usi_move[3]]
        
        piece_name = USI_TO_PIECE.get(piece_usi, piece_usi)
        to_file_zen = NUM_TO_ZENKAKU[to_file]
        to_rank_kan = NUM_TO_KANJI[to_rank]
        
        # 打ち駒は「同」にはならない（空きマスにしか打てない）
        return f"{turn_mark}{to_file_zen}{to_rank_kan}{piece_name}打"
    
    # 通常の指し手（例: '7g7f', '7f7e+'）
    is_promote = usi_move.endswith('+')
    move_str = usi_move[:-1] if is_promote else usi_move
    
    # USI座標から変換用にfrom_usiを取得
    from_usi = move_str[:2]  # 例: "7g"
    to_usi = move_str[2:4]   # 例: "7f"
    
    from_file = int(move_str[0])
    from_rank = USI_RANK_TO_NUM[move_str[1]]
    to_file = int(move_str[2])
    to_rank = USI_RANK_TO_NUM[move_str[3]]
    
    to_file_zen = NUM_TO_ZENKAKU[to_file]
    to_rank_kan = NUM_TO_KANJI[to_rank]
    
    # 駒名を取得
    piece_name = ""
    if board is not None:
        try:
            piece_name = piece_name_from_board(board, from_usi)
        except Exception:
            piece_name = ""
    
    # 「同」の処理: 前回の移動先と今回の移動先が同じ場合
    use_same = (prev_to_square is not None and prev_to_square == to_usi)
    
    if use_same:
        # 「同」表記を使用
        if is_promote:
            return f"{turn_mark}同{piece_name}成"
        else:
            return f"{turn_mark}同{piece_name}"
    else:
        # 通常表記
        if is_promote:
            return f"{turn_mark}{to_file_zen}{to_rank_kan}{piece_name}成"
        else:
            return f"{turn_mark}{to_file_zen}{to_rank_kan}{piece_name}"
