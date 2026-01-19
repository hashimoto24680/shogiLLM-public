# -*- coding: utf-8 -*-
"""
将棋KIFコメンタリーデータのクレンジングスクリプト

不要なコメント（場所、食事、メディア情報など）を含む行を削除し、
対局解説に関連するコメントのみを残す。
"""

import re
import os
from pathlib import Path
from typing import Optional


def load_keywords(filepath: str) -> list[str]:
    """
    キーワードファイルを読み込む。

    Args:
        filepath: キーワードファイルのパス

    Returns:
        キーワードのリスト（空白区切りで分割）
    """
    keywords = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            # 1行目は説明文なのでスキップ
            if line and not line.startswith('不要な'):
                # スペースで区切られたキーワードを分割
                keywords.extend(line.split())
    return keywords


def is_move_line(line: str) -> bool:
    """
    棋譜行かどうか判定する。

    棋譜行は「数字 手順」の形式（例: "1 ２六歩(27)"）

    Args:
        line: 判定対象の行

    Returns:
        棋譜行の場合True
    """
    return bool(re.match(r'^\d+\s+', line.strip()))


def remove_sentences_with_keyword(line: str, keyword: str) -> str:
    """
    行内の特定キーワードを含む文のみを削除する。

    文は句点「。」で区切られた単位として扱う。

    Args:
        line: 処理対象の行
        keyword: 削除対象キーワード

    Returns:
        キーワードを含む文を除去した行
    """
    if keyword not in line:
        return line
    
    # 句点で分割して、キーワードを含まない文のみ残す
    sentences = re.split(r'(。)', line)
    result = []
    i = 0
    while i < len(sentences):
        sentence = sentences[i]
        # 句点も含めて処理
        if i + 1 < len(sentences) and sentences[i + 1] == '。':
            sentence_with_punct = sentence + sentences[i + 1]
            i += 2
        else:
            sentence_with_punct = sentence
            i += 1
        
        # キーワードを含まない文のみ残す
        if keyword not in sentence_with_punct:
            result.append(sentence_with_punct)
    
    return ''.join(result).strip()


def contains_keyword(line: str, keywords: list[str], sentence_only_keywords: list[str]) -> tuple[bool, str]:
    """
    キーワードを含むか判定し、適切に処理した行を返す。

    Args:
        line: 判定対象の行
        keywords: 行削除対象キーワードのリスト
        sentence_only_keywords: 文単位削除対象キーワードのリスト

    Returns:
        (削除すべきか, 処理後の行)
    """
    processed_line = line
    
    # まず文単位削除キーワードの処理
    for keyword in sentence_only_keywords:
        processed_line = remove_sentences_with_keyword(processed_line, keyword)
    
    # 処理後に空になった場合
    if not processed_line.strip():
        return True, ''
    
    # 行削除キーワードのチェック
    for keyword in keywords:
        if keyword in processed_line:
            return True, ''
    
    return False, processed_line


def cleanse_file(
    input_path: str, 
    keywords: list[str],
    sentence_only_keywords: list[str]
) -> tuple[Optional[list[str]], dict]:
    """
    ファイルをクレンジングする。

    Args:
        input_path: 入力ファイルパス
        keywords: 行削除対象キーワード
        sentence_only_keywords: 文単位削除対象キーワード

    Returns:
        (クレンジング後の行リスト or None, 統計情報)
        コメントが残らない場合はNoneを返す
    """
    stats = {
        'total_lines': 0,
        'move_lines': 0,
        'deleted_lines': 0,
        'remaining_comment_lines': 0
    }
    
    result_lines = []
    
    with open(input_path, 'r', encoding='utf-8') as f:
        for line in f:
            stats['total_lines'] += 1
            line = line.rstrip('\r\n')
            
            # 空行は保持
            if not line.strip():
                result_lines.append(line)
                continue
            
            # 棋譜行は保持
            if is_move_line(line):
                stats['move_lines'] += 1
                result_lines.append(line)
                continue
            
            # コメント行の処理
            should_delete, processed_line = contains_keyword(
                line, keywords, sentence_only_keywords
            )
            
            if should_delete:
                stats['deleted_lines'] += 1
            else:
                stats['remaining_comment_lines'] += 1
                result_lines.append(processed_line)
    
    # コメントが残らない場合はNoneを返す
    if stats['remaining_comment_lines'] == 0:
        return None, stats
    
    return result_lines, stats


def main():
    """メイン処理"""
    # パスの設定
    base_dir = Path(__file__).parent.parent
    keywords_file = base_dir / 'data' / 'LLM' / 'unnecessary_comments.txt'
    input_dir = base_dir / 'data' / 'kif_commentary'
    output_dir = base_dir / 'data' / 'kif_commentary_cleaned'
    
    # 出力ディレクトリの作成
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # キーワードの読み込み
    all_keywords = load_keywords(str(keywords_file))
    
    # 「分」は文単位削除の特別処理
    sentence_only_keywords = ['分']
    keywords = [k for k in all_keywords if k not in sentence_only_keywords]
    
    print(f"キーワード数: {len(keywords)} (行削除) + {len(sentence_only_keywords)} (文削除)")
    
    # 統計情報
    total_stats = {
        'processed_files': 0,
        'output_files': 0,
        'skipped_files': 0,
        'total_deleted_lines': 0
    }
    
    # 全ファイルの処理
    input_files = sorted(input_dir.glob('*.txt'))
    print(f"処理対象ファイル数: {len(input_files)}")
    
    for i, input_file in enumerate(input_files):
        if (i + 1) % 1000 == 0:
            print(f"処理中... {i + 1}/{len(input_files)}")
        
        result, stats = cleanse_file(
            str(input_file), keywords, sentence_only_keywords
        )
        
        total_stats['processed_files'] += 1
        total_stats['total_deleted_lines'] += stats['deleted_lines']
        
        if result is None:
            total_stats['skipped_files'] += 1
        else:
            output_file = output_dir / input_file.name
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write('\n'.join(result))
            total_stats['output_files'] += 1
    
    # 結果の表示
    print("\n=== クレンジング完了 ===")
    print(f"処理ファイル数: {total_stats['processed_files']}")
    print(f"出力ファイル数: {total_stats['output_files']}")
    print(f"スキップファイル数: {total_stats['skipped_files']} (コメントなし)")
    print(f"削除行数: {total_stats['total_deleted_lines']}")


if __name__ == '__main__':
    main()
