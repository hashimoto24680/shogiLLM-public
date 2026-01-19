# -*- coding: utf-8 -*-
"""
Maia2 v0.2.1テスト - 新モデルのvalue出力を確認

強AI（やねうら王）とのセットで、新モデルの勝率出力を確認する。
新モデルはsigmoid済みなので、ラッパーを使わず直接ONNX推論を行う。
"""

import numpy as np
import onnxruntime as ort
import cshogi
from cshogi.dlshogi import FEATURES1_NUM, FEATURES2_NUM, make_input_features, make_move_label

from src.simulation.engine_wrapper import YaneuraouWrapper, EngineConfig


# Maia2設定
RATE_MIN = 800
BIN_WIDTH = 100
MOVE_LABELS = 2187
MODEL_PATH = "models/model_v021.onnx"


# テスト局面
POSITIONS = {
    "初期局面（先手番・互角）": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
    "角換わり中盤（後手番・後手不利）": "ln1g3nl/1rs2kg2/p2ppp1pp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L w B2Pb 28",
    "角換わり中盤2（先手番・先手有利）": "ln1g4l/1rs2kg2/p2pppnpp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L b B2Pb 29",
    "棒銀終盤2（後手番・後手有利）": "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/3S3R1/L3KG1NL w BSPbgnp 30",
    "棒銀終盤（先手番・先手不利）": "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/7R1/L1S1KG1NL b BSPbgnp 29",
}


def encode_board(board):
    """盤面を特徴量に変換"""
    feature1 = np.zeros((FEATURES1_NUM, 9, 9), dtype=np.float32)
    feature2 = np.zeros((FEATURES2_NUM, 9, 9), dtype=np.float32)
    make_input_features(board, feature1, feature2)
    features = np.concatenate([feature1, feature2], axis=0)
    return np.transpose(features, (1, 2, 0))


def get_legal_mask(board):
    """合法手マスクを生成"""
    mask = np.zeros(MOVE_LABELS, dtype=np.float32)
    for move in board.legal_moves:
        label = make_move_label(move, board.turn)
        if 0 <= label < mask.size:
            mask[label] = 1.0
    return mask


def maia2_v021_predict(session, input_names, sfen, rating=2700):
    """Maia2 v0.2.1で推論（sigmoid適用なし = モデル側で処理済み）"""
    board = cshogi.Board()
    board.set_sfen(sfen)
    
    features = encode_board(board).astype(np.float32)
    legal_mask = get_legal_mask(board)
    rating_bin = (rating - RATE_MIN) // BIN_WIDTH
    
    inputs = {
        "board": features[np.newaxis, ...],
        "rating_self": np.array([rating_bin], dtype=np.int32),
        "rating_oppo": np.array([rating_bin], dtype=np.int32),
    }
    if "legal_moves" in input_names:
        inputs["legal_moves"] = legal_mask[np.newaxis, ...].astype(np.float32)
    
    outputs = session.run(None, inputs)
    
    # v0.2.1はsigmoid済みなので、そのまま勝率として扱う
    value = float(np.asarray(outputs[1]).reshape(-1)[0])
    return value


def main():
    engine_config = EngineConfig(byoyomi=5000)
    
    # Maia2 v0.2.1セッションを直接作成
    session = ort.InferenceSession(MODEL_PATH, providers=["CPUExecutionProvider"])
    input_names = {inp.name for inp in session.get_inputs()}
    
    print("=" * 80)
    print("Maia2 v0.2.1 テスト（直接ONNX推論 - sigmoid適用なし）")
    print("=" * 80)
    print(f"{'局面':<30} | {'手番':^4} | {'やねうら王':^14} | {'Maia2 v0.2.1':^12} | {'期待'}")
    print("-" * 80)
    
    with YaneuraouWrapper(engine_config) as engine:
        for name, sfen in POSITIONS.items():
            turn = "先手" if sfen.split()[1] == "b" else "後手"
            
            # やねうら王の評価
            candidates = engine.analyze(sfen)
            engine_score = candidates[0].score if candidates else 0
            engine_wr = candidates[0].win_rate if candidates else 0.5
            
            # Maia2 v0.2.1の評価（直接推論）
            maia2_value = maia2_v021_predict(session, input_names, sfen)
            
            # 期待形勢を抽出
            if "有利" in name:
                expected = name.split("・")[1].replace("）", "")
            elif "不利" in name:
                expected = name.split("・")[1].replace("）", "")
            else:
                expected = "互角"
            
            print(f"{name[:30]:<30} | {turn:^4} | {engine_score:+5}cp ({engine_wr:5.1%}) | {maia2_value:5.1%} | {expected}")
    
    print("-" * 80)
    print("※やねうら王 = 手番側視点、Maia2 v0.2.1 = 手番側視点（sigmoid済み、適用なし）")


if __name__ == "__main__":
    main()
