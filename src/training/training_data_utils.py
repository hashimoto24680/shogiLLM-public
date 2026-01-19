# -*- coding: utf-8 -*-
"""Utilities for training data generation."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

from src.utils.KIF_to_usi import usi_move_to_kif


def load_commentary_data(input_dir: Path, min_length: int = 0) -> list[dict[str, Any]]:
    """
    kif_commentary_jsonディレクトリからすべてのJSONファイルを読み込む。

    Args:
        input_dir: 入力ディレクトリ
        min_length: コメントの最小文字数

    Returns:
        全コメントエントリのリスト（sfen, comment, move_number, source_file）
    """
    entries: list[dict[str, Any]] = []
    json_files = sorted(input_dir.glob("*.json"))

    for json_file in json_files:
        with open(json_file, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                for entry in data:
                    if len(entry.get("comment", "")) >= min_length:
                        entry["source_file"] = json_file.name
                        entries.append(entry)
            except json.JSONDecodeError:
                print(f"警告: JSONの読み込みに失敗しました ({json_file})")

    return entries


def win_rate_to_score(win_rate: float) -> int:
    """
    勝率をやねうら王のスコア（centipawn）に逆変換する。

    Args:
        win_rate: 勝率（0.0〜1.0）

    Returns:
        評価値（centipawn）
    """
    if win_rate <= 0.001:
        return -10000
    if win_rate >= 0.999:
        return 10000
    return int(-600 * math.log((1.0 / win_rate) - 1))


def collect_terminal_nodes(node: Any, path: list[str] | None = None) -> list[dict[str, Any]]:
    """
    TreeNodeから全末端局面を再帰的に収集する。

    Args:
        node: TreeNode
        path: ルートからの手順リスト

    Returns:
        list of (terminal_sfen, moves_path, terminal_score)
    """
    if path is None:
        path = []

    terminals: list[dict[str, Any]] = []

    current_path = path + ([node.move] if node.move else [])

    if node.is_terminal or not node.children:
        yaneuraou_score = win_rate_to_score(node.strong_eval_win_rate)
        terminals.append(
            {
                "sfen": node.sfen,
                "moves": current_path,
                "score": yaneuraou_score,
                "strong_eval": node.strong_eval_win_rate,
                "weak_eval": node.weak_eval_win_rate,
            }
        )
    else:
        for child in node.children:
            terminals.extend(collect_terminal_nodes(child, current_path))

    return terminals


def moves_to_kif_format(moves: list[str], start_sfen: str) -> str:
    """
    USI形式の手順をKIF形式に変換する。

    Args:
        moves: USI形式の手のリスト
        start_sfen: 開始局面のSFEN

    Returns:
        KIF形式の手順文字列
    """
    import cshogi

    board = cshogi.Board(start_sfen)
    kif_moves = []
    prev_to_square = None  # 前回の移動先を追跡

    for usi_move in moves:
        try:
            kif_move = usi_move_to_kif(usi_move, board, prev_to_square)
            kif_moves.append(kif_move)
            
            # 今回の移動先を記録
            if '*' in usi_move:
                # 打ち駒の場合: 例 'B*5e' -> '5e'
                prev_to_square = usi_move[2:4]
            else:
                # 通常の移動: 例 '7g7f' or '7g7f+' -> '7f'
                move_str = usi_move[:-1] if usi_move.endswith('+') else usi_move
                prev_to_square = move_str[2:4]
            
            board.push_usi(usi_move)
        except Exception:
            kif_moves.append(usi_move)
            prev_to_square = None  # エラー時はリセット
            try:
                board.push_usi(usi_move)
            except Exception:
                break

    return " → ".join(kif_moves)


def format_seconds(seconds: float) -> str:
    """秒数を表示用の日本語表現に整形する。"""
    seconds = max(0.0, float(seconds))
    minutes, secs = divmod(int(seconds + 0.5), 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:d}時間{minutes:02d}分{secs:02d}秒"
    if minutes:
        return f"{minutes:d}分{secs:02d}秒"
    return f"{secs:d}秒"


def count_valid_jsonl_lines(path: Path) -> int:
    """JSONLの先頭から、正しいJSON行の数を数える（途中の壊れた行で打ち切り）。"""
    if not path.exists():
        return 0
    count = 0
    with open(path, "r", encoding="utf-8") as rf:
        for line in rf:
            stripped = line.strip()
            if not stripped:
                continue
            try:
                json.loads(stripped)
            except Exception:
                break
            count += 1
    return count
