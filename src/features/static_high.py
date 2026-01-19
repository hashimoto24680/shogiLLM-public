# -*- coding: utf-8 -*-
"""
高次元静的特徴の抽出

囲い認識、戦法認識、玉の安全度計算などの高次元特徴を抽出する。
"""

import math
from typing import Dict, List, Tuple

import cshogi

from src.features.models import CastlePattern, KingSafety, StrategyPattern
from src.features.patterns.castles import ALL_CASTLES, CastleCondition, CastleDefinition
from src.utils.coordinates import RANK_KANJI, RANK_TO_INDEX


# 駒種の日本語への変換マップ（cshogiの駒種番号 -> 日本語）
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


def _square_to_file_rank(square_name: str) -> Tuple[int, int]:
    """
    日本語座標からfile, rankを取得する。

    Args:
        square_name: 日本語座標（例: "7七"）

    Returns:
        (file, rank) のタプル。file は 0-8 (1筋-9筋)、rank は 0-8 (一段-九段)
    """
    file = int(square_name[0]) - 1
    rank = RANK_TO_INDEX[square_name[1]]
    return file, rank


def _file_rank_to_square(file: int, rank: int) -> str:
    """
    file, rank から日本語座標に変換する。

    Args:
        file: 筋（0-8）
        rank: 段（0-8）

    Returns:
        日本語座標（例: "7七"）
    """
    return f"{file + 1}{RANK_KANJI[rank]}"


def _mirror_square(square_name: str) -> str:
    """
    後手用にマスを反転する。

    先手視点の座標を後手視点に変換する。
    筋: 10 - file（例: 1筋 -> 9筋）
    段: 10 - rank（例: 一段 -> 九段）

    Args:
        square_name: 先手視点の日本語座標

    Returns:
        後手視点の日本語座標
    """
    file, rank = _square_to_file_rank(square_name)
    mirrored_file = 8 - file  # 9 - 1 - file = 8 - file
    mirrored_rank = 8 - rank  # 9 - 1 - rank = 8 - rank
    return _file_rank_to_square(mirrored_file, mirrored_rank)


def _calculate_distance(square1: str, square2: str) -> float:
    """
    2つのマス間のユークリッド距離を計算する。

    Args:
        square1: 日本語座標1
        square2: 日本語座標2

    Returns:
        ユークリッド距離（小数点以下1桁で丸め）
    """
    file1, rank1 = _square_to_file_rank(square1)
    file2, rank2 = _square_to_file_rank(square2)
    distance = math.sqrt((file1 - file2) ** 2 + (rank1 - rank2) ** 2)
    return round(distance, 1)


def _get_pieces_on_board(board: cshogi.Board, color: int) -> Dict[str, List[str]]:
    """
    盤上の駒の位置を取得する。

    Args:
        board: cshogiのBoardオブジェクト
        color: 手番（cshogi.BLACK または cshogi.WHITE）

    Returns:
        駒種 -> マスリスト の辞書（例: {"金": ["7八", "6七"], "銀": ["7七"]}）
    """
    pieces: Dict[str, List[str]] = {}

    for sq in range(81):
        piece = board.piece(sq)
        if piece is None or piece == 0:
            continue

        # 駒種と手番を取得
        # cshogiでは piece_to_piece_type() を使用
        piece_type = cshogi.piece_to_piece_type(piece)
        # 駒の色は値が16以上なら後手（WHITE）
        piece_color = cshogi.WHITE if piece >= 16 else cshogi.BLACK

        if piece_color != color:
            continue

        # 日本語座標に変換
        # cshogiのマス番号: file = sq // 9, rank = sq % 9
        file = sq // 9
        rank = sq % 9
        square_name = _file_rank_to_square(file, rank)

        # 駒種を日本語に変換
        if piece_type not in PIECE_TYPE_TO_JAPANESE:
            continue

        piece_name = PIECE_TYPE_TO_JAPANESE[piece_type]

        # 成駒は元の駒種として扱う場合がある（囲いパターンでは金として扱うものもある）
        # ここでは成駒をそのまま保持する

        if piece_name not in pieces:
            pieces[piece_name] = []
        pieces[piece_name].append(square_name)

    return pieces


def _calculate_condition_score(
    condition: CastleCondition,
    pieces: Dict[str, List[str]],
    used_pieces: Dict[str, set],
    is_gote: bool = False
) -> float:
    """
    1つの条件のスコアを計算する。

    Args:
        condition: 囲いの条件
        pieces: 盤上の駒位置マップ
        used_pieces: すでに使用された駒のマップ（駒種 -> 使用済みマスのセット）
        is_gote: 後手の場合はTrue（座標を反転する）

    Returns:
        条件のスコア（0.0 ～ weight）
    """
    piece_type = condition.piece_type
    target_positions = condition.positions

    # 後手の場合は座標を反転
    if is_gote:
        target_positions = [_mirror_square(pos) for pos in target_positions]

    # 否定条件（negated）の処理
    if condition.negated:
        # 否定条件: 指定位置にその駒がなければスコア加算
        piece_list = pieces.get(piece_type, [])
        for pos in target_positions:
            if pos in piece_list:
                # その位置に駒がある -> 条件不成立 -> スコア0
                return 0.0
        # どの位置にもその駒がない -> 条件成立 -> weight全額
        return condition.weight

    # 通常条件: 指定駒種の駒がないか確認
    if piece_type not in pieces:
        return 0.0

    piece_list = pieces[piece_type]

    # すでに使用した駒を除外
    available_pieces = [p for p in piece_list if p not in used_pieces.get(piece_type, set())]

    if not available_pieces:
        return 0.0

    # strict=True の場合: 完全一致のみ
    if condition.strict:
        for pos in target_positions:
            if pos in available_pieces:
                if piece_type not in used_pieces:
                    used_pieces[piece_type] = set()
                used_pieces[piece_type].add(pos)
                return condition.weight
        # 完全一致なし -> スコア0
        return 0.0

    # 通常条件: 各条件位置に対して、最も距離が近い駒を探す
    best_score = 0.0
    best_piece = None

    for pos in target_positions:
        for piece_sq in available_pieces:
            distance = _calculate_distance(pos, piece_sq)
            # スコア = max(0, weight - 距離 * 0.1)
            score = max(0.0, condition.weight - distance * 0.1)
            if score > best_score:
                best_score = score
                best_piece = piece_sq

    # 最適な駒を使用済みに追加
    if best_piece is not None:
        if piece_type not in used_pieces:
            used_pieces[piece_type] = set()
        used_pieces[piece_type].add(best_piece)

    return best_score



def _calculate_castle_confidence(
    castle: CastleDefinition,
    pieces: Dict[str, List[str]],
    is_gote: bool = False
) -> float:
    """
    囲いのconfidenceを計算する。

    Args:
        castle: 囲いの定義
        pieces: 盤上の駒位置マップ
        is_gote: 後手の場合はTrue

    Returns:
        confidence値（0.0 ～ 1.0）
    """
    used_pieces: Dict[str, set] = {}
    total_weight = 0.0
    total_score = 0.0

    for condition in castle.conditions:
        total_weight += condition.weight

        score = _calculate_condition_score(condition, pieces, used_pieces, is_gote)

        # 必須条件がスコア0の場合 -> 囲い不成立
        if condition.required and score == 0.0:
            return 0.0

        total_score += score

    if total_weight == 0.0:
        return 0.0

    return total_score / total_weight


def recognize_castles(board: cshogi.Board) -> List[CastlePattern]:
    """
    囲いを認識する。

    patterns/castles.pyのALL_CASTLESを使用して、
    先手・後手それぞれの囲いを認識する。

    Args:
        board: cshogiのBoardオブジェクト

    Returns:
        認識された囲いパターンのリスト（CastlePattern）

    Examples:
        >>> import cshogi
        >>> board = cshogi.Board()
        >>> castles = recognize_castles(board)
        >>> len(castles)  # 初期局面では囲いなし
        0
    """
    results: List[CastlePattern] = []

    # 先手の駒を取得
    sente_pieces = _get_pieces_on_board(board, cshogi.BLACK)

    # 後手の駒を取得
    gote_pieces = _get_pieces_on_board(board, cshogi.WHITE)

    # 各囲いをチェック
    for castle in ALL_CASTLES:
        # 先手の囲いチェック
        sente_confidence = _calculate_castle_confidence(castle, sente_pieces, is_gote=False)
        if sente_confidence >= castle.min_confidence:
            results.append(CastlePattern(
                name=castle.name,
                color="先手",
                confidence=round(sente_confidence, 2)
            ))

        # 後手の囲いチェック（座標反転）
        gote_confidence = _calculate_castle_confidence(castle, gote_pieces, is_gote=True)
        if gote_confidence >= castle.min_confidence:
            results.append(CastlePattern(
                name=castle.name,
                color="後手",
                confidence=round(gote_confidence, 2)
            ))

    return results


def recognize_strategies(board: cshogi.Board) -> List[StrategyPattern]:
    """
    戦法を認識する。

    patterns/strategies.pyのALL_STRATEGIESを使用して、
    先手・後手それぞれの戦法を認識する。

    Args:
        board: cshogiのBoardオブジェクト

    Returns:
        認識された戦法パターンのリスト（StrategyPattern）

    Examples:
        >>> import cshogi
        >>> board = cshogi.Board()
        >>> strategies = recognize_strategies(board)
        >>> isinstance(strategies, list)
        True
    """
    from src.features.patterns.strategies import ALL_STRATEGIES, StrategyCondition, StrategyDefinition

    results: List[StrategyPattern] = []

    # 先手・後手の駒を取得
    sente_pieces = _get_pieces_on_board(board, cshogi.BLACK)
    gote_pieces = _get_pieces_on_board(board, cshogi.WHITE)

    # 持ち駒を取得
    sente_hand = _get_hand_pieces(board, cshogi.BLACK)
    gote_hand = _get_hand_pieces(board, cshogi.WHITE)

    # 各戦法をチェック
    for strategy in ALL_STRATEGIES:
        # 先手の戦法チェック
        sente_confidence = _calculate_strategy_confidence(
            strategy, sente_pieces, gote_pieces, sente_hand, gote_hand, is_gote=False
        )
        if sente_confidence >= strategy.min_confidence:
            results.append(StrategyPattern(
                name=strategy.name,
                color="先手",
                confidence=round(sente_confidence, 2)
            ))

        # 後手の戦法チェック（座標反転）
        gote_confidence = _calculate_strategy_confidence(
            strategy, gote_pieces, sente_pieces, gote_hand, sente_hand, is_gote=True
        )
        if gote_confidence >= strategy.min_confidence:
            results.append(StrategyPattern(
                name=strategy.name,
                color="後手",
                confidence=round(gote_confidence, 2)
            ))

    return results


def _get_hand_pieces(board: cshogi.Board, color: int) -> Dict[str, int]:
    """
    持ち駒を取得する。

    Args:
        board: cshogiのBoardオブジェクト
        color: 手番（cshogi.BLACK または cshogi.WHITE）

    Returns:
        駒種 -> 枚数 の辞書（例: {"歩": 2, "角": 1}）
    """
    hand_pieces: Dict[str, int] = {}

    # cshogiの持ち駒取得（hand配列を使用）
    hand = board.pieces_in_hand[color]

    # 駒種マッピング（インデックス -> 日本語）
    hand_piece_types = [
        (cshogi.PAWN, "歩"),
        (cshogi.LANCE, "香"),
        (cshogi.KNIGHT, "桂"),
        (cshogi.SILVER, "銀"),
        (cshogi.GOLD, "金"),
        (cshogi.BISHOP, "角"),
        (cshogi.ROOK, "飛"),
    ]

    for piece_type, japanese_name in hand_piece_types:
        count = hand[piece_type - 1]  # cshogiではインデックスが1ずれる場合がある
        if count > 0:
            hand_pieces[japanese_name] = count

    return hand_pieces


def _calculate_strategy_condition_score(
    condition,  # StrategyCondition
    my_pieces: Dict[str, List[str]],
    opp_pieces: Dict[str, List[str]],
    my_hand: Dict[str, int],
    opp_hand: Dict[str, int],
    used_pieces: Dict[str, set],
    is_gote: bool = False
) -> float:
    """
    戦法の1つの条件のスコアを計算する。

    Args:
        condition: 戦法の条件
        my_pieces: 自分の盤上の駒
        opp_pieces: 相手の盤上の駒
        my_hand: 自分の持ち駒
        opp_hand: 相手の持ち駒
        used_pieces: すでに使用された駒のマップ
        is_gote: 後手視点かどうか

    Returns:
        条件のスコア（0.0 ～ weight）
    """
    piece_type = condition.piece_type
    condition_type = condition.condition_type
    side = condition.side

    # 使用する駒セットを決定
    # side="sente" は「判定対象プレイヤー（自分）の駒」を意味する
    # side="gote" は「相手プレイヤーの駒」を意味する
    # is_gote は「後手の戦法を判定しているかどうか」を表す
    if side == "sente":
        # 自分の駒を使う
        pieces = my_pieces
        hand = my_hand
    else:  # side == "gote"
        # 相手の駒を使う
        pieces = opp_pieces
        hand = opp_hand

    # 条件タイプ別の処理
    if condition_type == "piece_in_hand":
        # 持ち駒条件
        if piece_type in hand and hand[piece_type] > 0:
            return condition.weight
        return 0.0

    elif condition_type == "piece_on_file":
        # 筋条件
        if condition.files is None:
            return 0.0

        piece_list = pieces.get(piece_type, [])
        # is_gote なら筋も反転
        target_files = condition.files
        if is_gote and side == "sente":
            target_files = [10 - f for f in condition.files]
        elif is_gote and side == "gote":
            # 相手視点は反転済み
            pass

        for sq in piece_list:
            file, _ = _square_to_file_rank(sq)
            file_num = file + 1  # 1-indexed
            if file_num in target_files:
                return condition.weight

        return 0.0

    else:  # condition_type == "piece_on"
        # マス条件（囲いと同様）
        if condition.positions is None:
            return 0.0

        target_positions = condition.positions
        # 後手視点の場合、座標を反転（sente側の条件のみ）
        if is_gote and side == "sente":
            target_positions = [_mirror_square(pos) for pos in target_positions]
        elif is_gote and side == "gote":
            # gote側の条件も反転が必要
            target_positions = [_mirror_square(pos) for pos in target_positions]

        piece_list = pieces.get(piece_type, [])
        available_pieces = [p for p in piece_list if p not in used_pieces.get(piece_type, set())]

        if not available_pieces:
            return 0.0

        # strict=True の場合: 完全一致のみ
        if condition.strict:
            for pos in target_positions:
                if pos in available_pieces:
                    if piece_type not in used_pieces:
                        used_pieces[piece_type] = set()
                    used_pieces[piece_type].add(pos)
                    return condition.weight
            # 完全一致なし -> スコア0
            return 0.0

        # 通常条件: 距離ベースのスコア計算
        best_score = 0.0
        best_piece = None

        for pos in target_positions:
            for piece_sq in available_pieces:
                distance = _calculate_distance(pos, piece_sq)
                score = max(0.0, condition.weight - distance * 0.1)
                if score > best_score:
                    best_score = score
                    best_piece = piece_sq

        if best_piece is not None:
            if piece_type not in used_pieces:
                used_pieces[piece_type] = set()
            used_pieces[piece_type].add(best_piece)

        return best_score


def _calculate_strategy_confidence(
    strategy,  # StrategyDefinition
    my_pieces: Dict[str, List[str]],
    opp_pieces: Dict[str, List[str]],
    my_hand: Dict[str, int],
    opp_hand: Dict[str, int],
    is_gote: bool = False
) -> float:
    """
    戦法のconfidenceを計算する。

    Args:
        strategy: 戦法の定義
        my_pieces: 自分の盤上の駒
        opp_pieces: 相手の盤上の駒
        my_hand: 自分の持ち駒
        opp_hand: 相手の持ち駒
        is_gote: 後手視点かどうか

    Returns:
        confidence値（0.0 ～ 1.0）
    """
    used_pieces: Dict[str, set] = {}
    total_weight = 0.0
    total_score = 0.0

    for condition in strategy.conditions:
        total_weight += condition.weight

        score = _calculate_strategy_condition_score(
            condition, my_pieces, opp_pieces, my_hand, opp_hand, used_pieces, is_gote
        )

        # 必須条件がスコア0の場合 -> 戦法不成立
        if condition.required and score == 0.0:
            return 0.0

        total_score += score

    if total_weight == 0.0:
        return 0.0

    return total_score / total_weight


def calculate_king_safety(board: cshogi.Board, color: str) -> KingSafety:
    """
    玉の安全度を計算する。

    Args:
        board: cshogiのBoardオブジェクト
        color: 手番（\"先手\" または \"後手\"）

    Returns:
        玉の安全度情報（KingSafety）

    計算式:
        gold_count: 隣接マスの金駒×2 + 2マス離れの金駒 - 2マス以内の敵駒
            ※金駒 = 金・銀
        density: 玉から2マス以内の自駒数 / 2マス以内のマス数
        safety_score: gold_count * 10 + density * 50
    """
    cshogi_color = cshogi.BLACK if color == "先手" else cshogi.WHITE
    enemy_color = cshogi.WHITE if color == "先手" else cshogi.BLACK

    # 玉の位置を探す
    king_sq = None
    king_square = "5九"  # デフォルト
    for sq in range(81):
        piece = board.piece(sq)
        if piece is None or piece == 0:
            continue
        piece_type = cshogi.piece_to_piece_type(piece)
        piece_color = cshogi.WHITE if piece >= 16 else cshogi.BLACK
        if piece_type == cshogi.KING and piece_color == cshogi_color:
            king_sq = sq
            file = sq // 9
            rank = sq % 9
            king_square = _file_rank_to_square(file, rank)
            break

    if king_sq is None:
        # 玉が見つからない場合はデフォルト値を返す
        return KingSafety(
            color=color,
            king_square=king_square,
            gold_count=0,
            density=0.0,
            safety_score=0
        )

    king_file = king_sq // 9
    king_rank = king_sq % 9

    # 2マス以内のマスを取得
    squares_within_1 = []  # 隣接マス（距離1）
    squares_within_2 = []  # 距離2のマス
    all_squares_within_2 = []  # 距離2以内のすべてのマス

    for df in range(-2, 3):
        for dr in range(-2, 3):
            if df == 0 and dr == 0:
                continue  # 玉自身は除く

            new_file = king_file + df
            new_rank = king_rank + dr

            if 0 <= new_file <= 8 and 0 <= new_rank <= 8:
                new_sq = new_file * 9 + new_rank
                distance = max(abs(df), abs(dr))  # チェビシェフ距離

                all_squares_within_2.append(new_sq)
                if distance == 1:
                    squares_within_1.append(new_sq)
                elif distance == 2:
                    squares_within_2.append(new_sq)

    # 金駒スコアを計算
    # 隣接マスの金駒×2 + 2マス離れの金駒 - 2マス以内の敵駒
    gold_count = 0

    # 隣接マスの金駒をカウント
    for sq in squares_within_1:
        piece = board.piece(sq)
        if piece is None or piece == 0:
            continue
        piece_type = cshogi.piece_to_piece_type(piece)
        piece_color = cshogi.WHITE if piece >= 16 else cshogi.BLACK

        if piece_color == cshogi_color:
            # 金駒（金・銀）なら+2
            if piece_type in [cshogi.GOLD, cshogi.SILVER]:
                gold_count += 2
        else:
            # 敵駒なら-1
            gold_count -= 1

    # 2マス離れの金駒をカウント
    for sq in squares_within_2:
        piece = board.piece(sq)
        if piece is None or piece == 0:
            continue
        piece_type = cshogi.piece_to_piece_type(piece)
        piece_color = cshogi.WHITE if piece >= 16 else cshogi.BLACK

        if piece_color == cshogi_color:
            # 金駒（金・銀）なら+1
            if piece_type in [cshogi.GOLD, cshogi.SILVER]:
                gold_count += 1
        else:
            # 敵駒なら-1
            gold_count -= 1

    # 密集度を計算
    # 玉から2マス以内の自駒数 / 2マス以内のマス数
    own_piece_count = 0
    for sq in all_squares_within_2:
        piece = board.piece(sq)
        if piece is None or piece == 0:
            continue
        piece_color = cshogi.WHITE if piece >= 16 else cshogi.BLACK
        if piece_color == cshogi_color:
            own_piece_count += 1

    total_squares = len(all_squares_within_2)
    density = own_piece_count / total_squares if total_squares > 0 else 0.0

    # 総合安全度スコアを計算
    safety_score = int(gold_count * 10 + density * 50)

    return KingSafety(
        color=color,
        king_square=king_square,
        gold_count=gold_count,
        density=round(density, 2),
        safety_score=safety_score
    )


def calculate_piece_activity(
    board: cshogi.Board,
    wrapper: "DlshogiWrapper" = None,
    model_path: str = "models/model-dr2_exhi.onnx"
) -> Dict[str, int]:
    """
    各駒の働きを計算する（dlshogi_wrapper使用）。

    駒の働き = 通常評価値 - その駒の利きをマスクした評価値
    正の値 = その駒が局面に貢献している
    負の値 = その駒が局面にマイナス影響

    Args:
        board: cshogiのBoardオブジェクト
        wrapper: DlshogiWrapperインスタンス（省略時は新規作成）
        model_path: dlshogiモデルファイルのパス

    Returns:
        日本語座標 -> 活動度 の辞書（例: {"7七": 50, "8八": -30}）
        玉は計算対象外

    Examples:
        >>> import cshogi
        >>> board = cshogi.Board()
        >>> activity = calculate_piece_activity(board)
        >>> isinstance(activity, dict)
        True
    """
    from src.features.dlshogi_wrapper import DlshogiWrapper

    # wrapperが渡されなければ新規作成
    own_wrapper = wrapper is None
    if own_wrapper:
        wrapper = DlshogiWrapper(model_path)
        wrapper.load()

    try:
        sfen = board.sfen()

        # 通常の評価値を取得
        base_prediction = wrapper.predict(sfen)
        base_score = base_prediction.score

        activity: Dict[str, int] = {}

        # 各マスの駒について計算
        for sq in range(81):
            piece = board.piece(sq)
            if piece is None or piece == 0:
                continue

            # 玉は計算対象外（マスクしても意味がない）
            piece_type = cshogi.piece_to_piece_type(piece)
            if piece_type == cshogi.KING:
                continue

            # 駒の利きをマスクして評価
            masked_prediction = wrapper.predict_with_masked_effects(sfen, sq)
            masked_score = masked_prediction.score

            # 駒の働き = 基準評価値 - マスク後評価値
            # base_scoreは手番側視点なので、
            # 手番側の駒: その駒をマスクすると評価が下がる = 正の働き
            # 相手側の駒: その駒をマスクすると評価が上がる = 計算上は負になる
            # → 相手側の駒の働きは反転して正にする必要がある
            piece_activity = base_score - masked_score
            
            # 駒の手番を確認
            piece_color = cshogi.WHITE if piece >= 16 else cshogi.BLACK
            
            # 手番でない側の駒は符号を反転
            # （相手の駒をマスクすると自分の評価が上がるため、計算上負になるが、
            #   実際には相手にとって正の働きをしている）
            if piece_color != board.turn:
                piece_activity = -piece_activity

            # 日本語座標に変換
            file = sq // 9
            rank = sq % 9
            square_name = _file_rank_to_square(file, rank)

            activity[square_name] = piece_activity

        return activity

    finally:
        if own_wrapper:
            wrapper.unload()

