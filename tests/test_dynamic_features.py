# -*- coding: utf-8 -*-
"""
動的特徴抽出のテストスクリプト

2つの局面の動的特徴を抽出し、data/feature に出力する。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

import json
from dataclasses import asdict

from src.features import FeatureExtractor


# テスト用局面
SFEN_BEFORE = "ln1g3nl/1ks1gr3/1ppppsbpp/p4pp2/7P1/P1P1P1P2/1P1PSP2P/1BKS3R1/LNG1G2NL b - 1"
SFEN_AFTER = "ln1g4l/1ks3rb1/1pp1pgnpp/p2p1pR2/7P1/P1P1PS3/1P1P1P2P/1BKS5/LNG1G2NL b S2p 13"

# 間の手順
MOVES_BETWEEN = [
    "4g4f",  # ▲４六銀
    "6c6d",  # △６四歩
    "3g3e",  # ▲３五歩
    "4b3b",  # △３二飛
    "3e3d",  # ▲３四歩
    "4c3d",  # △同　銀
    "2h3h",  # ▲３八飛
    "3a2b",  # △２二角
    "3i3c+", # ▲３三歩（成らずでなければ要修正）
    "2a3c",  # △同　桂
    "3h3d",  # ▲３四飛
    "5b4c",  # △４三金
]


def print_static_features(features, label: str):
    """静的特徴を表示する。"""
    print(f"\n{'='*60}")
    print(f"【{label}】")
    print(f"{'='*60}")
    print(f"SFEN: {features.sfen}")
    
    print(f"\n--- dlshogi評価値 ---")
    if features.dlshogi_score is not None:
        print(f"  評価値: {features.dlshogi_score:+d}")
    else:
        print("  評価値: 未計算")

    print(f"\n--- 駒得 ---")
    if features.material:
        print(f"  先手: {features.material.sente_score}点")
        print(f"  後手: {features.material.gote_score}点")
        print(f"  差分: {features.material.advantage}点")
        print(f"  説明: {features.material.description}")
    
    print(f"\n--- 玉の安全度 ---")
    for ks in features.king_safety:
        print(f"  {ks.color}:")
        print(f"    玉位置: {ks.king_square}")
        print(f"    金駒スコア: {ks.gold_count}")
        print(f"    密集度: {ks.density}")
        print(f"    安全度: {ks.safety_score}")
    
    print(f"\n--- 囲い ---")
    if features.castles:
        for castle in features.castles:
            print(f"  {castle.color}: {castle.name} (信頼度: {castle.confidence:.0%})")
    else:
        print("  なし")
    
    print(f"\n--- 戦法 ---")
    if features.strategies:
        for strategy in features.strategies:
            print(f"  {strategy.color}: {strategy.name} (信頼度: {strategy.confidence:.0%})")
    else:
        print("  なし")
    
    print(f"\n--- 持ち駒 ---")
    for hand in features.hand_pieces:
        if hand.pieces:
            pieces_str = ", ".join(f"{k}{v}枚" for k, v in hand.pieces.items() if v > 0)
            print(f"  {hand.color}: {pieces_str if pieces_str else 'なし'}")
        else:
            print(f"  {hand.color}: なし")
    
    print(f"\n--- 盤面（駒があるマス、働き順） ---")
    pieces_with_activity = []
    for sq in features.squares:
        if sq.piece is not None:
            pieces_with_activity.append((sq.square, sq.piece))
    # activity順にソート（降順）
    pieces_with_activity.sort(key=lambda x: x[1].activity, reverse=True)
    for square, piece in pieces_with_activity:
        print(f"  {square}: {piece.color}{piece.piece_type} (働き: {piece.activity:+d})")


def print_dynamic_features(dynamic):
    """動的特徴を表示する。"""
    print(f"\n{'#'*60}")
    print(f"【動的特徴（差分）】")
    print(f"{'#'*60}")
    
    print(f"\n--- 手順 ---")
    if dynamic.moves_between:
        print(f"  {' → '.join(dynamic.moves_between)}")
    else:
        print("  不明")
    
    print(f"\n--- 評価値の変化 ---")
    if dynamic.score_change is not None:
        print(f"  変化量: {dynamic.score_change:+d}")
        if dynamic.score_change > 0:
            print("  → 先手有利に変化")
        elif dynamic.score_change < 0:
            print("  → 後手有利に変化")
        else:
            print("  → 変化なし")
    else:
        print("  未計算")
    
    print(f"\n--- 駒得の変化 ---")
    print(f"  変化量: {dynamic.material_change:+d}点")
    if dynamic.material_change > 0:
        print("  → 先手有利に変化")
    elif dynamic.material_change < 0:
        print("  → 後手有利に変化")
    else:
        print("  → 変化なし")
    
    print(f"\n--- 安全度の変化 ---")
    print(f"  先手: {dynamic.sente_safety_change:+d}")
    print(f"  後手: {dynamic.gote_safety_change:+d}")


def features_to_dict(features):
    """特徴をシリアライズ可能な辞書に変換する。"""
    # dataclassをdictに変換（ネストしたdataclassも対応）
    def convert(obj):
        if hasattr(obj, '__dataclass_fields__'):
            return {k: convert(v) for k, v in asdict(obj).items()}
        elif isinstance(obj, list):
            return [convert(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: convert(v) for k, v in obj.items()}
        else:
            return obj
    
    return convert(features)


def squares_to_dict(squares):
    """squaresをシリアライズ可能な辞書に変換する。"""
    result = {}
    for sq in squares:
        sq_dict = {
            "square": sq.square,
            "attack_balance": sq.attack_balance,
        }
        if sq.piece:
            sq_dict["piece"] = {
                "piece_type": sq.piece.piece_type,
                "color": sq.piece.color,
                "square": sq.piece.square,
                "attack_squares": sq.piece.attack_squares,
                "movable_squares": sq.piece.movable_squares,
                "activity": sq.piece.activity,
            }
        if sq.adjacent:
            sq_dict["adjacent"] = sq.adjacent
        if sq.direct_attackers:
            sq_dict["direct_attackers"] = [
                {"piece_type": a.piece_type, "color": a.color, "square": a.square}
                for a in sq.direct_attackers
            ]
        if sq.indirect_attackers:
            sq_dict["indirect_attackers"] = [
                {"piece_type": a.piece_type, "color": a.color, "square": a.square}
                for a in sq.indirect_attackers
            ]
        result[sq.square] = sq_dict
    return result


def main():
    """メイン処理。"""
    print("=" * 60)
    print("動的特徴抽出テスト")
    print("=" * 60)
    
    # FeatureExtractor を初期化（dlshogiをデフォルトでロード）
    extractor = FeatureExtractor()
    
    # 静的特徴を抽出
    before = extractor.extract_static(SFEN_BEFORE)
    after = extractor.extract_static(SFEN_AFTER)
    
    # 動的特徴を抽出
    dynamic = extractor.extract_dynamic(SFEN_BEFORE, SFEN_AFTER, MOVES_BETWEEN)
    
    # 結果を表示
    print_static_features(before, "変化前")
    print_static_features(after, "変化後")
    print_dynamic_features(dynamic)
    
    # data/feature に出力
    output_dir = Path("data/feature")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    output_file = output_dir / "dynamic_features_test.json"
    
    # JSONに変換して保存
    output_data = {
        "before": {
            "sfen": before.sfen,
            "dlshogi_score": before.dlshogi_score,
            "sente_activity_total": before.sente_activity_total,
            "gote_activity_total": before.gote_activity_total,
            "material": features_to_dict(before.material) if before.material else None,
            "king_safety": [features_to_dict(ks) for ks in before.king_safety],
            "castles": [features_to_dict(c) for c in before.castles],
            "strategies": [features_to_dict(s) for s in before.strategies],
            "hand_pieces": [features_to_dict(h) for h in before.hand_pieces],
            "squares": squares_to_dict(before.squares),
        },
        "after": {
            "sfen": after.sfen,
            "dlshogi_score": after.dlshogi_score,
            "sente_activity_total": after.sente_activity_total,
            "gote_activity_total": after.gote_activity_total,
            "material": features_to_dict(after.material) if after.material else None,
            "king_safety": [features_to_dict(ks) for ks in after.king_safety],
            "castles": [features_to_dict(c) for c in after.castles],
            "strategies": [features_to_dict(s) for s in after.strategies],
            "hand_pieces": [features_to_dict(h) for h in after.hand_pieces],
            "squares": squares_to_dict(after.squares),
        },
        "dynamic": {
            "moves_between": dynamic.moves_between,
            "score_change": dynamic.score_change,
            "material_change": dynamic.material_change,
            "material_change_description": dynamic.material_change_description,
            "sente_safety_change": dynamic.sente_safety_change,
            "gote_safety_change": dynamic.gote_safety_change,
            "sente_activity_change": dynamic.sente_activity_change,
            "gote_activity_change": dynamic.gote_activity_change,
        },
    }
    
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_data, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 結果を {output_file} に保存しました。")


if __name__ == "__main__":
    main()
