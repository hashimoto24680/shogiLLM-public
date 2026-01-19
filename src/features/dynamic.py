# -*- coding: utf-8 -*-
"""
動的特徴抽出モジュール

2つの局面の静的特徴を比較してDynamicFeaturesを生成する。
"""

from __future__ import annotations

import cshogi

from src.features.models import DynamicFeatures, StaticFeatures
from src.features.material import (
    get_piece_counts_from_board,
    generate_material_change_description,
)


def extract_dynamic_features(
    before: StaticFeatures,
    after: StaticFeatures,
    moves_between: list[str] | None = None
) -> DynamicFeatures:
    """
    2つの静的特徴を比較してDynamicFeaturesを生成する。

    駒得の変化と安全度の変化を自動計算する。

    Args:
        before: 変化前の静的特徴
        after: 変化後の静的特徴
        moves_between: 間の手順（USI形式）。Noneは不明/直接比較。

    Returns:
        DynamicFeatures: 2つの局面の比較結果（駒得変化、安全度変化を含む）

    Examples:
        >>> from src.features.extractor import FeatureExtractor
        >>> extractor = FeatureExtractor()
        >>> before = extractor.extract_static(sfen1)
        >>> after = extractor.extract_static(sfen2)
        >>> dynamic = extract_dynamic_features(before, after, ["7g7f", "3c3d"])
        >>> print(dynamic.material_change)  # 駒得の変化
    """
    # 駒得の変化を計算
    material_change = 0
    if before.material and after.material:
        material_change = after.material.advantage - before.material.advantage

    # 安全度の変化を計算
    sente_safety_change = 0
    gote_safety_change = 0

    # 先手の安全度変化
    before_sente = next((ks for ks in before.king_safety if ks.color == "先手"), None)
    after_sente = next((ks for ks in after.king_safety if ks.color == "先手"), None)
    if before_sente and after_sente:
        sente_safety_change = after_sente.safety_score - before_sente.safety_score

    # 後手の安全度変化
    before_gote = next((ks for ks in before.king_safety if ks.color == "後手"), None)
    after_gote = next((ks for ks in after.king_safety if ks.color == "後手"), None)
    if before_gote and after_gote:
        gote_safety_change = after_gote.safety_score - before_gote.safety_score

    # 評価値の変化を計算
    score_change = None
    if before.dlshogi_score is not None and after.dlshogi_score is not None:
        score_change = after.dlshogi_score - before.dlshogi_score

    # 駒交換の説明を計算（beforeからafterの変化）
    material_change_description = ""
    promotions = []
    try:
        before_board = cshogi.Board(before.sfen)
        after_board = cshogi.Board(after.sfen)
        before_sente_count, before_gote_count = get_piece_counts_from_board(before_board)
        after_sente_count, after_gote_count = get_piece_counts_from_board(after_board)
        material_change_description = generate_material_change_description(
            before_sente_count,
            before_gote_count,
            after_sente_count,
            after_gote_count,
        )
        
        
        # 成駒検出: 盤面の差分から検出（盤上の成駒の数が増えているか）
        promoted_pieces = {
            9: 'と', 10: '成香', 11: '成桂', 12: '成銀', 13: '馬', 14: '竜',
            25: 'と', 26: '成香', 27: '成桂', 28: '成銀', 29: '馬', 30: '竜'
        }
        
        # 盤上の成駒カウント
        from collections import Counter
        before_counts = Counter()
        after_counts = Counter()
        
        for sq in range(81):
            if before_board.piece(sq) in promoted_pieces:
                before_counts[before_board.piece(sq)] += 1
            if after_board.piece(sq) in promoted_pieces:
                after_counts[after_board.piece(sq)] += 1
        
        # 差分検出
        for piece_id, name in promoted_pieces.items():
            diff = after_counts[piece_id] - before_counts[piece_id]
            if diff > 0:
                turn = "先手" if piece_id < 16 else "後手"
                for _ in range(diff):
                    promotions.append(f"{turn}に{name}")

    except Exception:
        pass

    # 駒の働き合計の変化
    sente_activity_change = after.sente_activity_total - before.sente_activity_total
    gote_activity_change = after.gote_activity_total - before.gote_activity_total

    return DynamicFeatures(
        before=before,
        after=after,
        moves_between=moves_between,
        material_change=material_change,
        sente_safety_change=sente_safety_change,
        gote_safety_change=gote_safety_change,
        score_change=score_change,
        material_change_description=material_change_description,
        sente_activity_change=sente_activity_change,
        gote_activity_change=gote_activity_change,
        promotions=promotions,
    )
