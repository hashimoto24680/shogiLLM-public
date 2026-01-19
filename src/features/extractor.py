# -*- coding: utf-8 -*-
"""
局面特徴生成エンジン（統合API）

静的特徴・動的特徴の抽出を統合した高レベルAPIを提供する。
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import cshogi

from src.features.dynamic import extract_dynamic_features
from src.features.material import calculate_material_from_board, MaterialAdvantage
from src.features.models import (
    DynamicFeatures,
    HandPieces,
    KingSafety,
    SquareInfo,
    StaticFeatures,
    CastlePattern,
    StrategyPattern,
)
from src.features.static_high import (
    recognize_castles,
    recognize_strategies,
    calculate_king_safety,
    calculate_piece_activity,
)
from src.features.static_low import extract_all_squares, extract_hand_pieces

# dlshogi_wrapperは必須ではないため、インポートエラーを許容
try:
    from src.features.dlshogi_wrapper import DlshogiWrapper
    HAS_DLSHOGI = True
except ImportError:
    HAS_DLSHOGI = False


# デフォルトのモデルパス
DEFAULT_MODEL_PATH = "models/model-dr2_exhi.onnx"


class FeatureExtractor:
    """
    局面特徴生成エンジン

    静的特徴（81マス情報、持ち駒、駒得、玉安全度、囲い、戦法）と
    動的特徴（2つの局面の比較）を抽出する統合API。

    Attributes:
        dlshogi_wrapper: dlshogiラッパー（駒の働き計算用、Noneの場合は計算しない）

    Examples:
        >>> extractor = FeatureExtractor()
        >>> features = extractor.extract_static(sfen)
        >>> print(features.sfen)
    """

    def __init__(self, dlshogi_model_path: str | None = DEFAULT_MODEL_PATH):
        """
        局面特徴生成エンジンを初期化する。

        Args:
            dlshogi_model_path: dlshogiモデルパス（評価値計算用）。
                Noneの場合は評価値計算をスキップ。
        """
        self.dlshogi_wrapper: DlshogiWrapper | None = None
        
        if dlshogi_model_path is not None and HAS_DLSHOGI:
            self.dlshogi_wrapper = DlshogiWrapper(dlshogi_model_path)
            self.dlshogi_wrapper.load()

    def extract_static(self, sfen: str) -> StaticFeatures:
        """
        静的特徴を抽出する。

        81マス情報、持ち駒、駒得、囲い、戦法、dlshogi評価値を抽出する。

        Args:
            sfen: 局面のSFEN文字列

        Returns:
            StaticFeatures: 静的特徴

        Examples:
            >>> extractor = FeatureExtractor()
            >>> features = extractor.extract_static("lnsgkgsnl/...")
            >>> len(features.squares)
            81
        """
        board = cshogi.Board(sfen)

        # 81マス情報
        squares = extract_all_squares(board)

        # 持ち駒
        hand_pieces = extract_hand_pieces(board)

        # 駒得
        material = calculate_material_from_board(board)

        # 玉安全度
        king_safety = [
            calculate_king_safety(board, "先手"),
            calculate_king_safety(board, "後手"),
        ]

        # 囲い認識
        castles = recognize_castles(board)

        # 戦法認識
        strategies = recognize_strategies(board)

        # dlshogi評価値と駒の働き
        dlshogi_score = None
        sente_activity_total = 0
        gote_activity_total = 0
        
        if self.dlshogi_wrapper is not None:
            prediction = self.dlshogi_wrapper.predict(sfen)
            # DlshogiWrapper の score は「手番側視点」。
            # 特徴量側は『先手有利=正』で統一したいのでここで正規化する。
            dlshogi_score = prediction.score if board.turn == cshogi.BLACK else -prediction.score

            # 駒の働きを計算
            activity_map = calculate_piece_activity(board, self.dlshogi_wrapper)
            
            # squaresのpiece.activityに設定 & 合計を計算
            for sq_info in squares:
                if sq_info.piece is not None:
                    activity = activity_map.get(sq_info.square, 0)
                    sq_info.piece.activity = activity
                    if sq_info.piece.color == "先手":
                        sente_activity_total += activity
                    else:
                        gote_activity_total += activity

        return StaticFeatures(
            sfen=sfen,
            squares=squares,
            hand_pieces=hand_pieces,
            material=material,
            king_safety=king_safety,
            castles=castles,
            strategies=strategies,
            dlshogi_score=dlshogi_score,
            sente_activity_total=sente_activity_total,
            gote_activity_total=gote_activity_total,
        )

    def extract_dynamic(
        self,
        sfen_before: str,
        sfen_after: str,
        moves_between: list[str] | None = None,
    ) -> DynamicFeatures:
        """
        2つの局面の静的特徴を比較する。

        Args:
            sfen_before: 変化前の局面（SFEN）
            sfen_after: 変化後の局面（SFEN）
            moves_between: 間の手順（USI形式）。Noneは不明/直接比較。

        Returns:
            DynamicFeatures: 2つの局面の比較結果
        """
        before = self.extract_static(sfen_before)
        after = self.extract_static(sfen_after)
        return extract_dynamic_features(before, after, moves_between)

    def to_text(self, features: StaticFeatures | DynamicFeatures) -> str:
        """
        特徴をLLM入力用テキストに変換する。

        Args:
            features: 静的特徴または動的特徴

        Returns:
            LLM入力用のテキスト
        """
        if isinstance(features, StaticFeatures):
            return self._static_to_text(features)
        elif isinstance(features, DynamicFeatures):
            return self._dynamic_to_text(features)
        else:
            raise TypeError(f"Unsupported feature type: {type(features)}")

    def _static_to_text(self, features: StaticFeatures) -> str:
        """静的特徴をテキストに変換する。"""
        lines = []
        lines.append(f"【局面】{features.sfen}")
        lines.append("")

        # dlshogi評価値
        if features.dlshogi_score is not None:
            lines.append(f"【評価値】{features.dlshogi_score:+d}")
            lines.append("")

        # 手番
        try:
            sfen_parts = features.sfen.split()
            if len(sfen_parts) >= 2:
                side = "先手" if sfen_parts[1] == "b" else "後手"
                lines.append(f"【手番】{side}")
                lines.append("")
        except Exception:
            pass

        # 持ち駒（駒得の上に配置）
        lines.append("【持ち駒】")
        for hand in features.hand_pieces:
            if hand.pieces:
                pieces_str = ", ".join(f"{k}{v}枚" for k, v in hand.pieces.items() if v > 0)
                lines.append(f"  {hand.color}: {pieces_str if pieces_str else 'なし'}")
            else:
                lines.append(f"  {hand.color}: なし")
        lines.append("")

        # 駒得（点数表示を追加、持ち駒記述は削除）
        if features.material:
            advantage_str = features.material.description
            if features.material.advantage != 0:
                advantage_str += f" ({abs(features.material.advantage)}点)"
            lines.append(f"【駒得】{advantage_str}")
            lines.append("")

        # 玉安全度
        if features.king_safety:
            lines.append("【玉安全度】")
            for ks in features.king_safety:
                lines.append(f"  {ks.color}: {ks.safety_score} (玉位置: {ks.king_square}, 金駒スコア: {ks.gold_count}, 密集度: {ks.density:.2f})")
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

        # 駒の働き合計
        if features.sente_activity_total != 0 or features.gote_activity_total != 0:
            lines.append("【駒の働き合計】")
            lines.append(f"  先手: {features.sente_activity_total:+d}")
            lines.append(f"  後手: {features.gote_activity_total:+d}")
            lines.append("")

        # 駒の働き（上位5駒）
        pieces_with_activity = []
        for sq in features.squares:
            if sq.piece is not None and sq.piece.activity != 0:
                pieces_with_activity.append((sq.square, sq.piece))
        if pieces_with_activity:
            # 働きの絶対値が大きい順に
            pieces_with_activity.sort(key=lambda x: abs(x[1].activity), reverse=True)
            lines.append("【駒の働き】(上位5駒)")
            for square, piece in pieces_with_activity[:5]:
                lines.append(f"  {square} {piece.color}{piece.piece_type}: {piece.activity:+d}")
            lines.append("")

        # 盤面情報（全81マス）
        lines.append("【盤面】")
        for sq in features.squares:
            if sq.piece is not None:
                piece = sq.piece
                attack_str = ", ".join(piece.attack_squares) if piece.attack_squares else "なし"
                movable_str = ", ".join(piece.movable_squares) if piece.movable_squares else "なし"
                lines.append(f"  {sq.square}: {piece.color}{piece.piece_type}")
                lines.append(f"    利きマス: {attack_str}")
                lines.append(f"    移動可能: {movable_str}")
                if piece.activity != 0:
                    lines.append(f"    駒の働き: {piece.activity:+d}")
                if sq.direct_attackers:
                    direct_str = ", ".join(f"{a.color}{a.piece_type}({a.square})" for a in sq.direct_attackers)
                    lines.append(f"    直接利き元: {direct_str}")
                if sq.indirect_attackers:
                    indirect_str = ", ".join(f"{a.color}{a.piece_type}({a.square})" for a in sq.indirect_attackers)
                    lines.append(f"    間接利き元: {indirect_str}")
                lines.append(f"    利きバランス: {sq.attack_balance:+d}")
            else:
                # 空きマス
                lines.append(f"  {sq.square}: 空き")
                if sq.direct_attackers:
                    direct_str = ", ".join(f"{a.color}{a.piece_type}({a.square})" for a in sq.direct_attackers)
                    lines.append(f"    直接利き元: {direct_str}")
                if sq.indirect_attackers:
                    indirect_str = ", ".join(f"{a.color}{a.piece_type}({a.square})" for a in sq.indirect_attackers)
                    lines.append(f"    間接利き元: {indirect_str}")
                if sq.attack_balance != 0:
                    lines.append(f"    利きバランス: {sq.attack_balance:+d}")

        return "\n".join(lines)

    def _dynamic_to_text(self, features: DynamicFeatures) -> str:
        """動的特徴をテキストに変換する。"""
        lines = []
        
        # 末端局面SFEN
        lines.append(f"【考えられる変化】{features.after.sfen}")
        lines.append("")
        
        # 手順（最初に表示）
        if features.moves_between:
            moves_str = " → ".join(features.moves_between)
            lines.append(f"【手順】{moves_str}")
            lines.append("")
        
        # 動的差分（評価値変化など）の詳述
        lines.append("【差分詳細】")
        
        # 評価値を先に表示、次に評価値変化（絶対値）
        if features.after.dlshogi_score is not None:
            lines.append(f"  評価値: {features.after.dlshogi_score:+d}")
        if features.score_change is not None:
            direction = "先手有利に" if features.score_change > 0 else "後手有利に" if features.score_change < 0 else ""
            lines.append(f"  評価値変化: {abs(features.score_change)} {direction}")
        
        # 成駒発生
        if features.promotions:
            lines.append(f"  成駒発生: {', '.join(features.promotions)}")
        
        # 駒の損得変化（絶対値表記）
        if features.material_change != 0:
            direction = "先手有利に" if features.material_change > 0 else "後手有利に"
            lines.append(f"  駒の損得変化: {abs(features.material_change)}点 {direction}")
        
        # 駒交換の説明
        if features.material_change_description:
            lines.append(f"  駒交換の説明: {features.material_change_description}")
        
        # 安全度変化
        if features.sente_safety_change != 0:
            lines.append(f"  先手安全度変化: {features.sente_safety_change:+d}")
        if features.gote_safety_change != 0:
            lines.append(f"  後手安全度変化: {features.gote_safety_change:+d}")
        
        # 駒の働き変化
        if features.sente_activity_change != 0:
            lines.append(f"  先手駒働き変化: {features.sente_activity_change:+d}")
        if features.gote_activity_change != 0:
            lines.append(f"  後手駒働き変化: {features.gote_activity_change:+d}")

        return "\n".join(lines)

    def __del__(self):
        """リソースを解放する。"""
        if self.dlshogi_wrapper is not None:
            self.dlshogi_wrapper.unload()
