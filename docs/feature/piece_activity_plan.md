# 駒の働き計算機能 実装プラン

## 概要

**目的**: 各駒が局面評価にどれだけ寄与しているかを数値化する「駒の働き」特徴量を算出する。

**使用モデル**: `models/model-dr2_exhi.onnx`（dlshogi WCSC32 電竜戦エキシビジョンモデル）

**原理**: 
1. 局面の評価値を取得（dlshogiモデルでvalue出力）
2. 特定の駒の利きをマスクした状態で再評価
3. 両者の差分 = その駒の働き

---

## 実装フェーズ

### Phase 1: dlshogiラッパー作成

**目的**: 特徴量をマスクせず、普通に局面のpolicyとvalueを取得できるようにする。

### Phase 2: 駒の働き計算

**目的**: Phase 1のラッパーを拡張し、特徴量マスキングによる駒の働きを計算。

---

## Phase 1: dlshogiラッパー実装

### 前提知識

#### dlshogi入力特徴量

`cshogi.dlshogi.make_input_features()` で生成:
- `features1`: shape `(62, 81)` → `(62, 9, 9)`
- `features2`: shape `(57, 81)` → `(57, 9, 9)`（持ち駒情報）

#### features1チャンネル構造

| チャンネル | 内容 |
|-----------|------|
| 0-13 | 先手の駒配置（歩,香,桂,銀,金,角,飛,王,と,成香,成桂,成銀,馬,龍） |
| 14-27 | **先手の駒の利き**（同上の順） |
| 28-30 | 先手の利き数（1, 2, 3以上） |
| 31-44 | 後手の駒配置 |
| 45-58 | **後手の駒の利き** |
| 59-61 | 後手の利き数 |

#### ONNX入出力

**入力**:
- `input1`: features1 (float32, shape: [batch, 62, 9, 9])
- `input2`: features2 (float32, shape: [batch, 57, 9, 9])

**出力**:
- `output_policy`: 方策（shape: [batch, 2187]）
- `output_value`: 価値（shape: [batch, 1]、sigmoid済み 0.0~1.0）

### 実装: src/features/dlshogi_wrapper.py

```python
# -*- coding: utf-8 -*-
"""
dlshogi ONNX推論ラッパー

DeepLearningShogiのモデルを使用して局面のpolicyとvalueを取得する。
"""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Tuple

import cshogi
import numpy as np
import onnxruntime as ort
from cshogi import dlshogi


# dlshogi定数
FEATURES1_NUM = dlshogi.FEATURES1_NUM  # 62
FEATURES2_NUM = dlshogi.FEATURES2_NUM  # 57
MOVE_LABELS = 2187


@dataclass
class DlshogiPrediction:
    """
    dlshogiの予測結果。

    Attributes:
        policy: 方策ベクトル（shape: (2187,)）
        value: 勝率（0.0~1.0、手番側視点）
        score: 評価値（centipawn、手番側視点）
    """
    policy: np.ndarray
    value: float
    score: int


def win_rate_to_score(win_rate: float) -> int:
    """
    勝率(0.0~1.0)を評価値(centipawn)に変換する。
    score_to_win_rateの逆関数。
    結果は-33000〜33000の範囲にクリップされる。
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
    """

    def __init__(self, model_path: str):
        """
        Args:
            model_path: ONNXモデルファイルのパス
        """
        self.model_path = Path(model_path)
        self._session: Optional[ort.InferenceSession] = None

    def load(self) -> None:
        """モデルをロードする。"""
        if not self.model_path.exists():
            raise FileNotFoundError(f"モデルが見つかりません: {self.model_path}")
        
        self._session = ort.InferenceSession(
            str(self.model_path),
            providers=['CUDAExecutionProvider', 'CPUExecutionProvider']
        )

    def unload(self) -> None:
        """モデルをアンロードする。"""
        self._session = None

    def make_features(self, board: cshogi.Board) -> Tuple[np.ndarray, np.ndarray]:
        """
        盤面からdlshogi形式の特徴量を生成する。

        Args:
            board: cshogiのBoardオブジェクト

        Returns:
            features1: shape (62, 9, 9)
            features2: shape (57, 9, 9)
        """
        features1 = np.zeros((FEATURES1_NUM, 81), dtype=np.float32)
        features2 = np.zeros((FEATURES2_NUM, 81), dtype=np.float32)
        
        dlshogi.make_input_features(board, features1, features2)
        
        features1 = features1.reshape(FEATURES1_NUM, 9, 9)
        features2 = features2.reshape(FEATURES2_NUM, 9, 9)
        
        return features1, features2

    def predict_from_features(
        self,
        features1: np.ndarray,
        features2: np.ndarray
    ) -> DlshogiPrediction:
        """
        特徴量から直接予測する。

        Args:
            features1: shape (62, 9, 9)
            features2: shape (57, 9, 9)

        Returns:
            DlshogiPrediction
        """
        if self._session is None:
            self.load()

        # バッチ次元を追加
        x1 = features1[np.newaxis, ...].astype(np.float32)
        x2 = features2[np.newaxis, ...].astype(np.float32)

        # 推論
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

    def predict(self, sfen: str) -> DlshogiPrediction:
        """
        SFEN文字列から予測する。

        Args:
            sfen: 局面SFEN

        Returns:
            DlshogiPrediction
        """
        board = cshogi.Board(sfen)
        features1, features2 = self.make_features(board)
        return self.predict_from_features(features1, features2)

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unload()
        return False
```

### テスト: tests/test_dlshogi_wrapper.py

```python
import pytest
from src.features.dlshogi_wrapper import DlshogiWrapper

MODEL_PATH = "models/model.onnx"  # または適切なパス

def test_predict_initial_position():
    """初期局面で予測できること"""
    wrapper = DlshogiWrapper(MODEL_PATH)
    wrapper.load()
    
    sfen = "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1"
    result = wrapper.predict(sfen)
    
    # valueは0~1の範囲
    assert 0.0 <= result.value <= 1.0
    
    # policyは2187要素
    assert result.policy.shape == (2187,)
    
    # 評価値が範囲内
    assert -33000 <= result.score <= 33000
    
    wrapper.unload()

def test_predict_from_features():
    """特徴量から直接予測できること"""
    wrapper = DlshogiWrapper(MODEL_PATH)
    wrapper.load()
    
    import cshogi
    board = cshogi.Board()
    features1, features2 = wrapper.make_features(board)
    
    result = wrapper.predict_from_features(features1, features2)
    assert 0.0 <= result.value <= 1.0
    
    wrapper.unload()
```

---

## Phase 2: 駒の働き計算

Phase 1完了後に実装。

### 概要

特定の駒の利きチャンネルをゼロマスクし、評価値の差分を計算。

```python
def mask_piece_effect(features1: np.ndarray, piece_type_index: int, side: str) -> np.ndarray:
    """駒の利きチャンネルをマスクする"""
    masked = features1.copy()
    if side == "sente":
        channel = 14 + piece_type_index  # 14-27
    else:
        channel = 45 + piece_type_index  # 45-58
    masked[channel, :, :] = 0.0
    return masked
```

---

## 依存関係

```
既存:
- DeepLearningShogi/ (dlshogiリポジトリ)
- models/*.onnx (dlshogiモデル)

新規作成:
- src/features/dlshogi_wrapper.py (Phase 1)
- src/features/piece_activity.py (Phase 2)
- tests/test_dlshogi_wrapper.py
- tests/test_piece_activity.py
```

---

## モデルパス

既存のONNXモデル:
- `models/model.onnx`
- `models/model_v021.onnx`
- `models/epoch-003.onnx`

Phase 1実装時にどのモデルを使用するか確認が必要。
