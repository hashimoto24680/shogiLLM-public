# -*- coding: utf-8 -*-
"""
dlshogi ONNX推論ラッパー

DeepLearningShogiのモデルを使用して局面のpolicyとvalueを取得する。

Why:
    dlshogiのONNXモデルを直接使用することで、局面評価を取得し、
    駒の働き計算のベースとなる評価値を算出する。
"""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple

import cshogi
import numpy as np
import onnxruntime as ort
from cshogi import dlshogi

from src.utils.attacks import get_piece_attacks


# dlshogi定数
FEATURES1_NUM = dlshogi.FEATURES1_NUM  # 62
FEATURES2_NUM = dlshogi.FEATURES2_NUM  # 57
MOVE_LABELS = 2187


@dataclass
class DlshogiPrediction:
    """
    dlshogiの予測結果。

    Attributes:
        policy: 方策ベクトル。各合法手の確率分布を表す。shape: (2187,)
        value: 勝率。0.0~1.0の範囲で手番側視点の勝率を表す。
        score: 評価値。centipawn単位で手番側視点の有利度を表す。
    """
    policy: np.ndarray
    value: float
    score: int


@dataclass
class CandidateMove:
    """
    候補手情報。

    Attributes:
        usi: USI形式の指し手（例: "7g7f", "2g2f"）
        policy_prob: 方策確率（softmax後の値）
        label_index: policyラベルのインデックス
    """
    usi: str
    policy_prob: float
    label_index: int


def win_rate_to_score(win_rate: float) -> int:
    """
    勝率(0.0~1.0)を評価値(centipawn)に変換する。

    dlshogiの score_to_win_rate の逆関数。
    ロジスティック関数の逆関数を使用。

    Args:
        win_rate: 勝率。0.0~1.0の範囲。

    Returns:
        評価値。-33000〜33000の範囲にクリップ。

    Why:
        dlshogiはvalueとして勝率（確率）を出力するが、
        将棋では評価値（centipawn）での表現が一般的なため変換が必要。
        係数600はdlshogiの実装に準拠。
    """
    if win_rate <= 0.0:
        return -33000
    if win_rate >= 1.0:
        return 33000
    score = int(-600.0 * math.log(1.0 / win_rate - 1.0))
    return max(-33000, min(33000, score))


class DlshogiWrapper:
    """
    dlshogi ONNX推論ラッパー。

    Usage:
        wrapper = DlshogiWrapper("path/to/model.onnx")
        wrapper.load()
        result = wrapper.predict("lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1")
        print(f"勝率: {result.value:.2%}, 評価値: {result.score}")

    コンテキストマネージャとしても使用可能:
        with DlshogiWrapper("path/to/model.onnx") as wrapper:
            result = wrapper.predict(sfen)
    """

    def __init__(self, model_path: str):
        """
        ラッパーを初期化する。

        Args:
            model_path: ONNXモデルファイルのパス
        """
        self.model_path = Path(model_path)
        self._session: Optional[ort.InferenceSession] = None

    def load(self) -> None:
        """
        モデルをロードする。

        Raises:
            FileNotFoundError: モデルファイルが存在しない場合
        """
        if not self.model_path.exists():
            raise FileNotFoundError(f"モデルが見つかりません: {self.model_path}")

        self._session = ort.InferenceSession(
            str(self.model_path),
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )

    def unload(self) -> None:
        """モデルをアンロードしてメモリを解放する。"""
        self._session = None

    def make_features(self, board: cshogi.Board) -> Tuple[np.ndarray, np.ndarray]:
        """
        盤面からdlshogi形式の特徴量を生成する。

        Args:
            board: cshogiのBoardオブジェクト

        Returns:
            features1: 駒配置・利き情報。shape (62, 9, 9)
            features2: 持ち駒情報。shape (57, 9, 9)

        Note:
            cshogiのmake_input_featuresはメモリポインタを受け取るため、
            (N, 9, 9)形式で直接渡すことができる。
        """
        features1 = np.zeros((FEATURES1_NUM, 9, 9), dtype=np.float32)
        features2 = np.zeros((FEATURES2_NUM, 9, 9), dtype=np.float32)

        dlshogi.make_input_features(board, features1, features2)

        return features1, features2

    def predict_from_features(
        self,
        features1: np.ndarray,
        features2: np.ndarray
    ) -> DlshogiPrediction:
        """
        特徴量から直接予測する。

        駒の働き計算では特徴量をマスクして予測するため、
        このメソッドが必要。

        Args:
            features1: 駒配置・利き情報。shape (62, 9, 9)
            features2: 持ち駒情報。shape (57, 9, 9)

        Returns:
            DlshogiPrediction: 予測結果
        """
        if self._session is None:
            self.load()

        # バッチ次元を追加
        x1 = features1[np.newaxis, ...].astype(np.float32)
        x2 = features2[np.newaxis, ...].astype(np.float32)

        # 推論実行
        io_binding = self._session.io_binding()
        io_binding.bind_cpu_input('input1', x1)
        io_binding.bind_cpu_input('input2', x2)
        io_binding.bind_output('output_policy')
        io_binding.bind_output('output_value')
        self._session.run_with_iobinding(io_binding)

        policy, value = io_binding.copy_outputs_to_cpu()

        policy = policy[0]  # (2187,)
        value = float(value[0][0])  # スカラー
        score = win_rate_to_score(value)

        return DlshogiPrediction(
            policy=policy,
            value=value,
            score=score
        )

    def predict_with_masked_effects(
        self,
        sfen: str,
        square_index: int
    ) -> DlshogiPrediction:
        """
        指定したマスにある駒の利きをマスクして予測する。

        駒の働き計算で使用。指定した駒が利きを持たない状態での
        評価値を算出するため、その駒の利きチャンネルをマスクする。

        Args:
            sfen: 局面SFEN
            square_index: マスインデックス（0-80）

        Returns:
            DlshogiPrediction: 予測結果

        Note:
            features1の構造: [2][31][81] = [color][channel][square]
            - color: 0=手番側, 1=相手側
            - channel 0-13: 駒の配置（PieceType-1）
            - channel 14-27: 駒の利き（14 + PieceType-1）
            - channel 28-30: 利き数
        """
        board = cshogi.Board(sfen)
        features1, features2 = self.make_features(board)

        # 指定マスに駒があるか確認
        piece = board.piece(square_index)
        if piece == cshogi.NONE:
            # 駒がなければ通常予測
            return self.predict_from_features(features1, features2)

        # 駒種と色を取得
        piece_type = cshogi.piece_to_piece_type(piece)
        piece_color = cshogi.BLACK if piece < 16 else cshogi.WHITE

        # 手番に応じて特徴量上の色インデックスを決定
        # dlshogiは手番側を0、相手側を1としてエンコードする
        if board.turn == piece_color:
            color_index = 0  # 手番側
        else:
            color_index = 1  # 相手側

        attacks = get_piece_attacks(board, square_index, piece_type, piece_color)

        # 特徴量上のマス座標変換（後手番の場合は盤面が反転される）
        def transform_square(sq: int) -> int:
            if board.turn == cshogi.WHITE:
                return 80 - sq
            return sq

        # 駒の利きチャンネルをマスク
        # channel = 14 + (piece_type - 1)
        attack_channel = 14 + (piece_type - 1)
        full_channel_index = color_index * 31 + attack_channel
        
        # 利き数チャンネルのベースインデックス (28, 29, 30)
        attack_count_base = color_index * 31 + 28
        
        for attack_sq in attacks:
            # 特徴量上の座標に変換
            feature_sq = transform_square(attack_sq)
            # 9x9形式でのインデックス
            file_idx = feature_sq // 9
            rank_idx = feature_sq % 9
            
            # 駒の利きチャンネルをマスク
            features1[full_channel_index, file_idx, rank_idx] = 0.0
            
            # 利き数チャンネルを更新（1つ減らす）
            # 利き数は0,1,2の3チャンネルで表現
            # 現在の利き数を確認して1つ下げる
            if features1[attack_count_base + 2, file_idx, rank_idx] == 1.0:
                # 利き3 -> 利き2
                features1[attack_count_base + 2, file_idx, rank_idx] = 0.0
            elif features1[attack_count_base + 1, file_idx, rank_idx] == 1.0:
                # 利き2 -> 利き1
                features1[attack_count_base + 1, file_idx, rank_idx] = 0.0
            elif features1[attack_count_base + 0, file_idx, rank_idx] == 1.0:
                # 利き1 -> 利き0
                features1[attack_count_base + 0, file_idx, rank_idx] = 0.0

        return self.predict_from_features(features1, features2)


    def predict(self, sfen: str) -> DlshogiPrediction:
        """
        SFEN文字列から予測する。

        Args:
            sfen: 局面SFEN

        Returns:
            DlshogiPrediction: 予測結果
        """
        board = cshogi.Board(sfen)
        features1, features2 = self.make_features(board)
        return self.predict_from_features(features1, features2)

    def get_top_moves(
        self,
        sfen: str,
        top_n: int = 5
    ) -> Tuple[List[CandidateMove], float]:
        """
        上位N手の候補手とvalueを返す。

        合法手のみをフィルタリングし、policyの高い順にソート。

        Args:
            sfen: 局面SFEN
            top_n: 取得する候補手の数

        Returns:
            candidates: 候補手のリスト（policy降順）
            value: 勝率（手番側視点）

        Why:
            座標系が正しいか検証するため、policyラベルから
            USI形式の手に変換して確認する。
        """
        board = cshogi.Board(sfen)
        result = self.predict(sfen)

        # 合法手のラベルを取得
        legal_moves = list(board.legal_moves)
        legal_labels = {}
        for move in legal_moves:
            label = dlshogi.make_move_label(move, board.turn)
            usi = cshogi.move_to_usi(move)
            legal_labels[label] = usi

        # policyをsoftmaxして確率に変換
        policy = result.policy
        # 合法手のみのpolicyを取得
        legal_probs = []
        for label, usi in legal_labels.items():
            legal_probs.append((label, usi, policy[label]))

        # policy値でソート（降順）
        legal_probs.sort(key=lambda x: x[2], reverse=True)

        # softmax正規化
        max_logit = max(p[2] for p in legal_probs)
        exp_probs = [(label, usi, np.exp(logit - max_logit))
                     for label, usi, logit in legal_probs]
        total = sum(p[2] for p in exp_probs)
        normalized = [(label, usi, prob / total)
                      for label, usi, prob in exp_probs]

        # 上位N手を返す
        candidates = [
            CandidateMove(usi=usi, policy_prob=prob, label_index=label)
            for label, usi, prob in normalized[:top_n]
        ]

        return candidates, result.value

    def __enter__(self):
        """コンテキストマネージャのエントリーポイント。"""
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャの終了処理。"""
        self.unload()
        return False
