# -*- coding: utf-8 -*-
"""
Maia2 ONNX推論のラッパー

Maia2モデルを使用して、指定したレーティングの人間が
指しそうな手を予測する。
"""

import os
from dataclasses import dataclass
from pathlib import Path

import cshogi
import numpy as np
import onnxruntime as ort
from cshogi import KI2
from cshogi.dlshogi import FEATURES1_NUM, FEATURES2_NUM, make_input_features, make_move_label


# Maia2デフォルト設定
RATE_MIN = 800
RATE_MAX = 2800
BIN_WIDTH = 100
MOVE_LABELS = 2187
MOVE_END = 0  # cshogiでは0が終端マーカー

# デフォルトのモデルパス
DEFAULT_MODEL_PATH = os.path.join(
    os.path.dirname(__file__),
    "..", "..", "models", "model.onnx"
)


@dataclass
class Maia2Config:
    """
    Maia2設定を格納するデータクラス。
    
    Attributes:
        model_path: ONNXモデルファイルのパス
        rating_self: 予測対象のレーティング（800-2800）
        rating_oppo: 対戦相手のレーティング（省略時はrating_selfと同じ）
        top_k: 取得する候補手の数
    """
    model_path: str = DEFAULT_MODEL_PATH
    rating_self: int = 1500
    rating_oppo: int | None = None
    top_k: int = 5


@dataclass
class Maia2Prediction:
    """
    Maia2の予測結果を格納するデータクラス。
    
    Attributes:
        move: 最も確率が高い手（USI形式）
        probability: その手を指す確率
        value: 局面の勝率（0.0〜1.0）
        top_moves: 上位k個の候補手と確率のリスト
    """
    move: str
    probability: float
    value: float
    top_moves: list[tuple[str, float]]


def _bin_rating(rating: int) -> int:
    """レーティングをビン番号に変換する。"""
    if rating < RATE_MIN or rating >= RATE_MAX:
        raise ValueError(
            f"レーティングは {RATE_MIN} <= rating < {RATE_MAX} の範囲で指定してください (got: {rating})."
        )
    return (rating - RATE_MIN) // BIN_WIDTH


def _encode_board_dlshogi(board: cshogi.Board) -> np.ndarray:
    """盤面をdlshogi形式の特徴量に変換する。"""
    feature1 = np.zeros((FEATURES1_NUM, 9, 9), dtype=np.float32)
    feature2 = np.zeros((FEATURES2_NUM, 9, 9), dtype=np.float32)
    make_input_features(board, feature1, feature2)
    features = np.concatenate([feature1, feature2], axis=0)
    return np.transpose(features, (1, 2, 0))


def _get_legal_moves_mask(board: cshogi.Board) -> np.ndarray:
    """合法手のマスクを生成する。"""
    mask = np.zeros(MOVE_LABELS, dtype=np.float32)
    for move in board.legal_moves:
        if move == MOVE_END:
            continue
        label = make_move_label(move, board.turn)
        if 0 <= label < mask.size:
            mask[label] = 1.0
    return mask


def _softmax(logits: np.ndarray) -> np.ndarray:
    """ソフトマックス関数を適用する。"""
    logits = logits.astype(np.float32, copy=False)
    max_logit = float(np.max(logits))
    shifted = logits.astype(np.float64, copy=False) - max_logit
    exp = np.exp(shifted, dtype=np.float64)
    sum_exp = float(np.sum(exp))
    if not np.isfinite(sum_exp) or sum_exp <= 0.0:
        return np.zeros_like(logits, dtype=np.float32)
    probs = exp / sum_exp
    return probs.astype(np.float32, copy=False)


def _find_move_by_label(board: cshogi.Board, label: int) -> int | None:
    """ラベルから対応する手を探す。"""
    for move in board.legal_moves:
        if make_move_label(move, board.turn) == label:
            return move
    return None


class Maia2Wrapper:
    """
    Maia2 ONNX推論のラッパークラス。
    
    指定したレーティングの人間が指しそうな手を予測する。
    
    Attributes:
        config: Maia2設定
    """
    
    def __init__(self, config: Maia2Config | None = None):
        """
        Maia2ラッパーを初期化する。
        
        Args:
            config: Maia2設定。Noneの場合はデフォルト設定を使用。
        """
        self.config = config or Maia2Config()
        self._session: ort.InferenceSession | None = None
        self._input_names: set[str] = set()
    
    def load(self) -> None:
        """
        ONNXモデルをロードする。
        """
        path = Path(self.config.model_path).expanduser().resolve()
        if not path.exists():
            raise FileNotFoundError(f"ONNXモデルが見つかりません: {path}")
        
        self._session = ort.InferenceSession(
            path.as_posix(),
            providers=["CUDAExecutionProvider", "CPUExecutionProvider"]
        )
        self._input_names = {inp.name for inp in self._session.get_inputs()}
    
    def unload(self) -> None:
        """
        モデルをアンロードする。
        """
        self._session = None
        self._input_names = set()
    
    def predict(self, sfen: str) -> Maia2Prediction:
        """
        局面に対して人間らしい着手を予測する。
        
        Args:
            sfen: 分析対象の局面（SFEN形式）
            
        Returns:
            Maia2の予測結果
        """
        if self._session is None:
            self.load()
        
        # レーティングをビン番号に変換
        rating_self_bin = _bin_rating(self.config.rating_self)
        rating_oppo = self.config.rating_oppo or self.config.rating_self
        rating_oppo_bin = _bin_rating(rating_oppo)
        
        # 盤面をセット
        board = cshogi.Board()
        board.set_sfen(sfen)
        
        # 特徴量を生成
        features = _encode_board_dlshogi(board).astype(np.float32)
        legal_mask = _get_legal_moves_mask(board)
        
        # ONNX入力を準備
        inputs = {
            "board": features[np.newaxis, ...],
            "rating_self": np.array([rating_self_bin], dtype=np.int32),
            "rating_oppo": np.array([rating_oppo_bin], dtype=np.int32),
        }
        if "legal_moves" in self._input_names:
            inputs["legal_moves"] = legal_mask[np.newaxis, ...].astype(np.float32)
        
        # 推論実行
        outputs = self._session.run(None, inputs)
        
        policy_logits = np.asarray(outputs[0])[0].astype(np.float32)
        value_logit = float(np.asarray(outputs[1]).reshape(-1)[0])
        
        # 非合法手をマスキング
        masked_logits = np.array(policy_logits, copy=True)
        masked_logits[legal_mask < 0.5] = -1e4
        policy_probs = _softmax(masked_logits)
        
        # 勝率を計算
        value = float(1.0 / (1.0 + np.exp(-value_logit)))
        
        # 上位k個の候補手を取得
        top_k = self.config.top_k
        top_indices = np.argsort(policy_probs)[::-1][:top_k]
        
        top_moves = []
        for label in top_indices:
            label = int(label)
            prob = float(policy_probs[label])
            move = _find_move_by_label(board, label)
            if move is not None:
                move_usi = cshogi.move_to_usi(move)
                top_moves.append((move_usi, prob))
        
        # 最も確率が高い手
        best_move = top_moves[0][0] if top_moves else ""
        best_prob = top_moves[0][1] if top_moves else 0.0
        
        return Maia2Prediction(
            move=best_move,
            probability=best_prob,
            value=value,
            top_moves=top_moves,
        )
    
    def __enter__(self):
        """コンテキストマネージャーのenter。"""
        self.load()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """コンテキストマネージャーのexit。"""
        self.unload()
        return False
