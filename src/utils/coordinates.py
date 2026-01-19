# -*- coding: utf-8 -*-
"""
将棋盤座標変換ユーティリティ

cshogiにおける座標系の変換関数を提供する。

座標系の詳細はdocs/coordinate_system.mdを参照。
"""

# 段（rank）の日本語とインデックスの対応
RANK_KANJI = ['一', '二', '三', '四', '五', '六', '七', '八', '九']
RANK_TO_INDEX = {'一': 0, '二': 1, '三': 2, '四': 3, '五': 4,
                 '六': 5, '七': 6, '八': 7, '九': 8}


def japanese_to_index(notation: str) -> int:
    """
    日本語座標をマスインデックスに変換する。

    Args:
        notation: 日本語座標（例: "7七", "5五"）

    Returns:
        マスインデックス（0-80）

    Raises:
        ValueError: 無効な座標の場合

    Examples:
        >>> japanese_to_index("1一")
        0
        >>> japanese_to_index("5五")
        40
        >>> japanese_to_index("9九")
        80
    """
    if len(notation) != 2:
        raise ValueError(f"無効な座標: {notation}")

    try:
        file = int(notation[0]) - 1  # 筋（0-indexed）
    except ValueError:
        raise ValueError(f"無効な筋: {notation[0]}")

    if notation[1] not in RANK_TO_INDEX:
        raise ValueError(f"無効な段: {notation[1]}")

    rank = RANK_TO_INDEX[notation[1]]  # 段（0-indexed）

    if not (0 <= file <= 8):
        raise ValueError(f"筋は1-9の範囲: {notation}")

    return file * 9 + rank


def index_to_japanese(index: int) -> str:
    """
    マスインデックスを日本語座標に変換する。

    Args:
        index: マスインデックス（0-80）

    Returns:
        日本語座標（例: "7七"）

    Raises:
        ValueError: 無効なインデックスの場合

    Examples:
        >>> index_to_japanese(0)
        '1一'
        >>> index_to_japanese(40)
        '5五'
        >>> index_to_japanese(80)
        '9九'
    """
    if not (0 <= index <= 80):
        raise ValueError(f"インデックスは0-80の範囲: {index}")

    file = index // 9
    rank = index % 9
    return f"{file + 1}{RANK_KANJI[rank]}"


def usi_to_index(usi: str) -> int:
    """
    USI形式のマス表記をインデックスに変換する。

    Args:
        usi: USI形式のマス（例: "7g", "5e"）

    Returns:
        マスインデックス（0-80）

    Raises:
        ValueError: 無効なUSI形式の場合

    Examples:
        >>> usi_to_index("1a")
        0
        >>> usi_to_index("5e")
        40
        >>> usi_to_index("9i")
        80
    """
    if len(usi) != 2:
        raise ValueError(f"無効なUSI形式: {usi}")

    try:
        file = int(usi[0]) - 1
    except ValueError:
        raise ValueError(f"無効な筋: {usi[0]}")

    rank_char = usi[1].lower()
    if rank_char < 'a' or rank_char > 'i':
        raise ValueError(f"無効な段: {usi[1]}")

    rank = ord(rank_char) - ord('a')

    if not (0 <= file <= 8):
        raise ValueError(f"筋は1-9の範囲: {usi}")

    return file * 9 + rank


def index_to_usi(index: int) -> str:
    """
    インデックスをUSI形式に変換する。

    Args:
        index: マスインデックス（0-80）

    Returns:
        USI形式のマス（例: "7g"）

    Raises:
        ValueError: 無効なインデックスの場合

    Examples:
        >>> index_to_usi(0)
        '1a'
        >>> index_to_usi(40)
        '5e'
        >>> index_to_usi(80)
        '9i'
    """
    if not (0 <= index <= 80):
        raise ValueError(f"インデックスは0-80の範囲: {index}")

    file = index // 9
    rank = index % 9
    return f"{file + 1}{chr(ord('a') + rank)}"


def file_rank_to_index(file: int, rank: int) -> int:
    """
    file/rankからマスインデックスを計算する。

    Args:
        file: 筋（0-8、0=1筋）
        rank: 段（0-8、0=一段）

    Returns:
        マスインデックス（0-80）

    Raises:
        ValueError: 無効なfile/rankの場合

    Examples:
        >>> file_rank_to_index(0, 0)
        0
        >>> file_rank_to_index(4, 4)
        40
    """
    if not (0 <= file <= 8):
        raise ValueError(f"fileは0-8の範囲: {file}")
    if not (0 <= rank <= 8):
        raise ValueError(f"rankは0-8の範囲: {rank}")

    return file * 9 + rank


def index_to_file_rank(index: int) -> tuple:
    """
    マスインデックスからfile/rankを計算する。

    Args:
        index: マスインデックス（0-80）

    Returns:
        (file, rank) のタプル

    Raises:
        ValueError: 無効なインデックスの場合

    Examples:
        >>> index_to_file_rank(0)
        (0, 0)
        >>> index_to_file_rank(40)
        (4, 4)
    """
    if not (0 <= index <= 80):
        raise ValueError(f"インデックスは0-80の範囲: {index}")

    return index // 9, index % 9
