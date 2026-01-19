# -*- coding: utf-8 -*-
"""
KIF形式のコメント付き棋譜をJSON形式に変換するスクリプト

クレンジング済みKIFファイルを読み込み、各指し手の後の局面（SFEN）と
その局面に対するコメントのペアをJSON形式で出力する。
"""

import json
import re
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from cshogi import Board
from src.utils.KIF_to_usi import kif_move_to_usi


def is_move_line(line: str) -> tuple[bool, int | None, str | None]:
    """
    行が棋譜行かどうか判定する。

    Args:
        line: 判定対象の行

    Returns:
        (is_move, move_number, move_str): 棋譜行の場合は(True, 手数, 指し手)、
        そうでなければ(False, None, None)
    """
    match = re.match(r'^(\d+)\s+(.+)$', line.strip())
    if match:
        move_num = int(match.group(1))
        move_str = match.group(2).strip()
        # 「投了」などは棋譜行として扱わない
        if move_str in ('投了', '持将棋', '千日手', '中断'):
            return False, None, None
        return True, move_num, move_str
    return False, None, None


def parse_kif_with_comments(filepath: str) -> list[dict]:
    """
    KIFファイルを読み込み、コメント付き局面のリストを返す。

    Args:
        filepath: KIFファイルのパス

    Returns:
        コメント付き局面のリスト。各エントリは:
        {"sfen": "...", "comment": "...", "move_number": N}
    """
    with open(filepath, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    board = Board()
    results = []
    last_to_square = None
    current_sfen = None
    current_move_num = 0
    pending_comments = []

    for line in lines:
        line = line.rstrip('\r\n')

        is_move, move_num, move_str = is_move_line(line)

        if is_move:
            # 前の指し手にコメントがあれば保存
            if current_sfen and pending_comments:
                results.append({
                    'sfen': current_sfen,
                    'comment': '\n'.join(pending_comments),
                    'move_number': current_move_num
                })
            pending_comments = []

            # 指し手を処理
            try:
                usi_move, to_square = kif_move_to_usi(move_str, last_to_square)
                board.push_usi(usi_move)
                current_sfen = board.sfen()
                current_move_num = move_num
                last_to_square = to_square
            except ValueError as e:
                # 変換エラーの場合はスキップ
                print(f"警告 ({filepath}): {e}")
                current_sfen = None
            except Exception as e:
                # cshogiのエラー（不正な手など）
                print(f"警告 ({filepath}): 手 '{move_str}' を適用できません: {e}")
                current_sfen = None
        else:
            # コメント行（空行でない場合）
            if line.strip():
                pending_comments.append(line.strip())

    # 最後の指し手にコメントがあれば保存
    if current_sfen and pending_comments:
        results.append({
            'sfen': current_sfen,
            'comment': '\n'.join(pending_comments),
            'move_number': current_move_num
        })

    return results


def convert_file(input_path: Path, output_path: Path) -> dict:
    """
    1つのKIFファイルをJSONに変換する。

    Args:
        input_path: 入力KIFファイルのパス
        output_path: 出力JSONファイルのパス

    Returns:
        統計情報の辞書
    """
    results = parse_kif_with_comments(str(input_path))

    stats = {
        'comment_count': len(results),
        'converted': len(results) > 0
    }

    if results:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)

    return stats


def main():
    """メイン処理"""
    # パスの設定
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir / 'data' / 'kif_commentary_cleaned'
    output_dir = base_dir / 'data' / 'kif_commentary_json'

    # 出力ディレクトリの作成
    output_dir.mkdir(parents=True, exist_ok=True)

    # 統計情報
    total_stats = {
        'processed_files': 0,
        'output_files': 0,
        'skipped_files': 0,
        'total_comments': 0
    }

    # 全ファイルの処理
    input_files = sorted(input_dir.glob('*.txt'))
    print(f"処理対象ファイル数: {len(input_files)}")

    for i, input_file in enumerate(input_files):
        if (i + 1) % 1000 == 0:
            print(f"処理中... {i + 1}/{len(input_files)}")

        output_file = output_dir / f"{input_file.stem}.json"

        try:
            stats = convert_file(input_file, output_file)
            total_stats['processed_files'] += 1
            total_stats['total_comments'] += stats['comment_count']

            if stats['converted']:
                total_stats['output_files'] += 1
            else:
                total_stats['skipped_files'] += 1
        except Exception as e:
            print(f"エラー ({input_file}): {e}")
            total_stats['skipped_files'] += 1

    # 結果の表示
    print("\n=== 変換完了 ===")
    print(f"処理ファイル数: {total_stats['processed_files']}")
    print(f"出力ファイル数: {total_stats['output_files']}")
    print(f"スキップファイル数: {total_stats['skipped_files']}")
    print(f"総コメント数: {total_stats['total_comments']}")


if __name__ == '__main__':
    main()
