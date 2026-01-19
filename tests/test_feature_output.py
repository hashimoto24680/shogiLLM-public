# -*- coding: utf-8 -*-
"""
特徴抽出テキスト出力テスト

beforeの静的特徴をフル出力し、複数のafterに対してsquares以外の静的特徴と動的特徴を出力する。
結果はdata/feature/に.txtとして保存される。
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.features import FeatureExtractor
from src.features.dynamic import extract_dynamic_features
from src.features.models import StaticFeatures, DynamicFeatures


# テスト用の局面
SFEN_BEFORE = "ln1g3nl/1ks1gr3/1ppppsbpp/p4pp2/7P1/P1P1P1P2/1P1PSP2P/1BKS3R1/LNG1G2NL b - 1"

# 複数のafter局面
SFEN_AFTERS = [
    {
        "sfen": "ln1g4l/1ks3rb1/1pp1pgnpp/p2p1pR2/7P1/P1P1PS3/1P1P1P2P/1BKS5/LNG1G2NL b S2p 13",
        "moves": ["4g4f", "6c6d", "3g3e", "4b3b", "3e3d", "4c3d", "2h3h", "3a2b", "3i3c+", "2a3c", "3h3d", "5b4c"],
        "description": "銀得局面",
    },
]


def static_to_text_full(features: StaticFeatures) -> str:
    """静的特徴を全てテキストに変換（squaresを含む）。"""
    lines = []
    lines.append(f"【局面】{features.sfen}")
    lines.append("")

    # 評価値
    if features.dlshogi_score is not None:
        lines.append(f"【評価値】{features.dlshogi_score:+d}")
        lines.append("")

    # 駒得
    if features.material:
        lines.append(f"【駒得】{features.material.description}")
        if features.material.sente_hand:
            sente_hand_str = ", ".join(f"{k}{v}枚" for k, v in features.material.sente_hand.items() if v > 0)
            lines.append(f"  先手持ち駒: {sente_hand_str if sente_hand_str else 'なし'}")
        if features.material.gote_hand:
            gote_hand_str = ", ".join(f"{k}{v}枚" for k, v in features.material.gote_hand.items() if v > 0)
            lines.append(f"  後手持ち駒: {gote_hand_str if gote_hand_str else 'なし'}")
        lines.append("")

    # 玉安全度
    if features.king_safety:
        lines.append("【玉安全度】")
        for ks in features.king_safety:
            lines.append(f"  {ks.color}: {ks.safety_score} (玉位置: {ks.king_square})")
        lines.append("")

    # 囲い
    if features.castles:
        lines.append("【囲い】")
        for castle in features.castles:
            lines.append(f"  {castle.color}: {castle.name} (信頼度: {castle.confidence:.0%})")
        lines.append("")

    # 戦法
    if features.strategies:
        lines.append("【戦法】")
        for strategy in features.strategies:
            lines.append(f"  {strategy.color}: {strategy.name} (信頼度: {strategy.confidence:.0%})")
        lines.append("")

    # 持ち駒
    lines.append("【持ち駒】")
    for hand in features.hand_pieces:
        if hand.pieces:
            pieces_str = ", ".join(f"{k}{v}枚" for k, v in hand.pieces.items() if v > 0)
            lines.append(f"  {hand.color}: {pieces_str if pieces_str else 'なし'}")
        else:
            lines.append(f"  {hand.color}: なし")
    lines.append("")

    # 駒の働き合計
    lines.append("【駒の働き合計】")
    lines.append(f"  先手: {features.sente_activity_total:+d}")
    lines.append(f"  後手: {features.gote_activity_total:+d}")
    lines.append("")

    # 駒の働き（全駒）
    pieces_with_activity = []
    for sq in features.squares:
        if sq.piece is not None:
            pieces_with_activity.append((sq.square, sq.piece, sq))
    if pieces_with_activity:
        pieces_with_activity.sort(key=lambda x: abs(x[1].activity), reverse=True)
        lines.append("【駒の働き】")
        for square, piece, sq_info in pieces_with_activity:
            lines.append(f"  {square} {piece.color}{piece.piece_type}: {piece.activity:+d}")
    lines.append("")

    # 盤面情報（駒があるマス）
    lines.append("【盤面詳細】")
    for sq in features.squares:
        if sq.piece is not None:
            piece = sq.piece
            lines.append(f"  {sq.square}: {piece.color}{piece.piece_type}")
            if piece.attack_squares:
                lines.append(f"    利きマス: {', '.join(piece.attack_squares)}")
            if piece.movable_squares:
                lines.append(f"    移動可能: {', '.join(piece.movable_squares)}")
            if sq.direct_attackers:
                direct_str = ", ".join(f"{a.color}{a.piece_type}({a.square})" for a in sq.direct_attackers)
                lines.append(f"    直接利き元: {direct_str}")
            if sq.indirect_attackers:
                indirect_str = ", ".join(f"{a.color}{a.piece_type}({a.square})" for a in sq.indirect_attackers)
                lines.append(f"    間接利き元: {indirect_str}")
            lines.append(f"    利きバランス: {sq.attack_balance:+d}")

    return "\n".join(lines)


def static_to_text_without_squares(features: StaticFeatures) -> str:
    """静的特徴をテキストに変換（squaresを除く）。"""
    lines = []
    lines.append(f"【局面】{features.sfen}")
    lines.append("")

    # 評価値
    if features.dlshogi_score is not None:
        lines.append(f"【評価値】{features.dlshogi_score:+d}")
        lines.append("")

    # 駒得
    if features.material:
        lines.append(f"【駒得】{features.material.description}")
        if features.material.sente_hand:
            sente_hand_str = ", ".join(f"{k}{v}枚" for k, v in features.material.sente_hand.items() if v > 0)
            lines.append(f"  先手持ち駒: {sente_hand_str if sente_hand_str else 'なし'}")
        if features.material.gote_hand:
            gote_hand_str = ", ".join(f"{k}{v}枚" for k, v in features.material.gote_hand.items() if v > 0)
            lines.append(f"  後手持ち駒: {gote_hand_str if gote_hand_str else 'なし'}")
        lines.append("")

    # 玉安全度
    if features.king_safety:
        lines.append("【玉安全度】")
        for ks in features.king_safety:
            lines.append(f"  {ks.color}: {ks.safety_score} (玉位置: {ks.king_square})")
        lines.append("")

    # 囲い
    if features.castles:
        lines.append("【囲い】")
        for castle in features.castles:
            lines.append(f"  {castle.color}: {castle.name} (信頼度: {castle.confidence:.0%})")
        lines.append("")

    # 戦法
    if features.strategies:
        lines.append("【戦法】")
        for strategy in features.strategies:
            lines.append(f"  {strategy.color}: {strategy.name} (信頼度: {strategy.confidence:.0%})")
        lines.append("")

    # 持ち駒
    lines.append("【持ち駒】")
    for hand in features.hand_pieces:
        if hand.pieces:
            pieces_str = ", ".join(f"{k}{v}枚" for k, v in hand.pieces.items() if v > 0)
            lines.append(f"  {hand.color}: {pieces_str if pieces_str else 'なし'}")
        else:
            lines.append(f"  {hand.color}: なし")
    lines.append("")

    # 駒の働き合計
    lines.append("【駒の働き合計】")
    lines.append(f"  先手: {features.sente_activity_total:+d}")
    lines.append(f"  後手: {features.gote_activity_total:+d}")
    lines.append("")

    # 駒の働き（上位10駒のみ）
    pieces_with_activity = []
    for sq in features.squares:
        if sq.piece is not None and sq.piece.activity != 0:
            pieces_with_activity.append((sq.square, sq.piece))
    if pieces_with_activity:
        pieces_with_activity.sort(key=lambda x: abs(x[1].activity), reverse=True)
        lines.append("【駒の働き】(上位10駒)")
        for square, piece in pieces_with_activity[:10]:
            lines.append(f"  {square} {piece.color}{piece.piece_type}: {piece.activity:+d}")

    return "\n".join(lines)


def dynamic_to_text(dynamic: DynamicFeatures) -> str:
    """動的特徴をテキストに変換。"""
    lines = []

    # 手順
    if dynamic.moves_between:
        moves_str = " → ".join(dynamic.moves_between)
        lines.append(f"【手順】{moves_str}")
    lines.append("")

    # 評価値の変化
    lines.append("【評価値の変化】")
    if dynamic.score_change is not None:
        direction = "先手有利に" if dynamic.score_change > 0 else "後手有利に" if dynamic.score_change < 0 else ""
        lines.append(f"  変化量: {dynamic.score_change:+d} {direction}")
    lines.append("")

    # 駒得の変化
    lines.append("【駒得の変化】")
    lines.append(f"  変化量: {dynamic.material_change:+d}点")
    if dynamic.material_change_description:
        lines.append(f"  説明: {dynamic.material_change_description}")
    lines.append("")

    # 安全度の変化
    lines.append("【安全度の変化】")
    lines.append(f"  先手: {dynamic.sente_safety_change:+d}")
    lines.append(f"  後手: {dynamic.gote_safety_change:+d}")
    lines.append("")

    # 駒の働き合計の変化
    lines.append("【駒の働き合計の変化】")
    lines.append(f"  先手: {dynamic.sente_activity_change:+d}")
    lines.append(f"  後手: {dynamic.gote_activity_change:+d}")

    return "\n".join(lines)


def main():
    """メイン処理。"""
    print("=" * 60)
    print("特徴抽出テキスト出力テスト")
    print("=" * 60)

    # FeatureExtractor を初期化
    extractor = FeatureExtractor()

    # Before の静的特徴を抽出
    before = extractor.extract_static(SFEN_BEFORE)
    print(f"\nBefore局面を抽出完了: {SFEN_BEFORE}")

    # 出力用ディレクトリ
    output_dir = Path("data/feature")
    output_dir.mkdir(parents=True, exist_ok=True)

    # テキスト全体を構築
    output_lines = []
    output_lines.append("=" * 80)
    output_lines.append("特徴抽出結果")
    output_lines.append("=" * 80)
    output_lines.append("")

    # Before の静的特徴（フル出力）
    output_lines.append("#" * 80)
    output_lines.append("【BEFORE局面】（静的特徴 - フル出力）")
    output_lines.append("#" * 80)
    output_lines.append("")
    output_lines.append(static_to_text_full(before))
    output_lines.append("")

    # 各After局面について
    for i, after_info in enumerate(SFEN_AFTERS, 1):
        sfen_after = after_info["sfen"]
        moves = after_info.get("moves", None)
        description = after_info.get("description", f"After {i}")

        print(f"After局面 {i} ({description}) を抽出中...")

        # After の静的特徴を抽出
        after = extractor.extract_static(sfen_after)

        # 動的特徴を抽出
        dynamic = extract_dynamic_features(before, after, moves)

        output_lines.append("#" * 80)
        output_lines.append(f"【AFTER局面 {i}】{description}")
        output_lines.append("#" * 80)
        output_lines.append("")

        # After の静的特徴（squaresを除く）
        output_lines.append("-" * 40)
        output_lines.append("静的特徴（squaresを除く）")
        output_lines.append("-" * 40)
        output_lines.append("")
        output_lines.append(static_to_text_without_squares(after))
        output_lines.append("")

        # 動的特徴（beforeとの差分）
        output_lines.append("-" * 40)
        output_lines.append("動的特徴（BEFOREとの差分）")
        output_lines.append("-" * 40)
        output_lines.append("")
        output_lines.append(dynamic_to_text(dynamic))
        output_lines.append("")

    # ファイルに保存
    output_file = output_dir / "features_output.txt"
    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(output_lines))

    print(f"\n✅ 結果を {output_file} に保存しました。")


if __name__ == "__main__":
    main()
