# -*- coding: utf-8 -*-
from __future__ import annotations

from typing import TYPE_CHECKING
import json
from pathlib import Path

if TYPE_CHECKING:
    from .commentary_openai_rag import RagExample


def truncate_text(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def fmt_seconds(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    m, s = divmod(int(seconds + 0.5), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}時間{m:02d}分{s:02d}秒"
    if m:
        return f"{m:d}分{s:02d}秒"
    return f"{s:d}秒"


def strip_teacher_commentary(features_text: str) -> str:
    """features_text から教師の解説文セクションを除去する。"""
    marker = "【解説文】"
    idx = features_text.find(marker)
    if idx == -1:
        return features_text
    return features_text[:idx].rstrip()


def has_teacher_commentary_in_features(features_text: str) -> bool:
    """features_text 内に教師解説（【解説文】以降の非空テキスト）が含まれるか。"""
    marker = "【解説文】"
    idx = features_text.find(marker)
    if idx == -1:
        return False
    tail = features_text[idx + len(marker) :]
    return bool(tail.strip())


def compact_features_text(features_text: str, max_chars: int) -> str:
    """埋め込み/プロンプト用に features_text を短縮する。

    方針:
    - 末尾の教師解説は必ず除去
    - 「【盤面】」部分は1マス要約行を空白区切りで1行にまとめる
    - 「【シミュレーション結果】」以降の動的特徴も含める
    """
    text = strip_teacher_commentary(features_text)
    if max_chars <= 0:
        return ""

    board_marker = "【盤面】"
    sim_marker = "【シミュレーション結果】"
    
    board_idx = text.find(board_marker)
    sim_idx = text.find(sim_marker)
    
    if board_idx == -1:
        return truncate_text(text, max_chars)

    # 盤面より前の部分（静的特徴のヘッダー部分）
    head = text[:board_idx].rstrip()
    
    # 盤面部分の終了位置を特定
    if sim_idx != -1:
        board_section = text[board_idx:sim_idx]
        sim_section = text[sim_idx:]
    else:
        board_section = text[board_idx:]
        sim_section = ""
    
    # 盤面の1マス要約行を抽出して空白区切りに
    board_lines = board_section.splitlines()
    compact_board_items: list[str] = []
    for line in board_lines:
        stripped = line.lstrip()
        if not stripped:
            continue
        # 盤面の1マス要約行（例: "4八: 先手金"）のみ抽出
        if (
            len(stripped) >= 2
            and stripped[0] in "123456789"
            and stripped[1] in "一二三四五六七八九"
            and ":" in stripped
        ):
            # "4八: 先手金" の形式をそのまま使用
            compact_board_items.append(stripped)
    
    # 盤面を空白区切りの1行にまとめる
    if compact_board_items:
        compact_board = board_marker + " " + " ".join(compact_board_items)
    else:
        compact_board = ""
    
    # 結果を結合
    parts = [head]
    if compact_board:
        parts.append(compact_board)
    if sim_section:
        parts.append(sim_section.strip())
    
    combined = "\n\n".join(parts)
    return truncate_text(combined, max_chars)


def count_valid_jsonl_lines(path: Path) -> int:
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


def load_style_examples(jsonl_path: Path, max_count: int = 100) -> list[str]:
    """JSONLから解説文（commentary）のみを読み込む。
    
    Args:
        jsonl_path: 解説文を含むJSONLファイルのパス
        max_count: 読み込む最大件数
    
    Returns:
        解説文のリスト
    """
    examples: list[str] = []
    if not jsonl_path.exists():
        return examples
    
    with open(jsonl_path, "r", encoding="utf-8") as f:
        for line in f:
            if len(examples) >= max_count:
                break
            stripped = line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
                commentary = rec.get("commentary", "")
                if commentary and len(commentary) >= 50:  # 短すぎるものは除外
                    examples.append(commentary)
            except json.JSONDecodeError:
                continue
    
    return examples


def make_prompt(
    features_text_without_commentary: str,
    min_chars: int,
    max_chars: int,
    rag_examples: list["RagExample"] | None = None,
    use_full_features: bool = False,
    style_examples: list[str] | None = None,
) -> tuple[str, str]:
    """(system, user) を返す。
    
    Args:
        features_text_without_commentary: 解説文を除いた局面特徴テキスト
        min_chars: 生成する解説文の最小文字数目安
        max_chars: 生成する解説文の最大文字数目安
        rag_examples: RAGで取得した類似局面の参考例
        use_full_features: 参考例の局面特徴をフル表記で含めるか
        style_examples: 解説文のスタイル例（言い回しを学習させる用）
    """
    # スタイル例のセクション
    style_section = ""
    if style_examples:
        style_lines = []
        for i, ex in enumerate(style_examples, start=1):
            # 解説文を短く切り詰める（最大200文字）
            truncated = ex[:200] + "…" if len(ex) > 200 else ex
            style_lines.append(f"例{i}: {truncated}")
        style_section = (
            "\n## 解説の文体例（以下の言い回しを参考にする）\n"
            + "\n".join(style_lines)
            + "\n"
        )
    
    system = (
        "あなたは将棋のプロ棋士レベルの解説者です。\n"
        "入力は『局面特徴（テキスト）』です。そこから、読者向けの自然な日本語の解説文を生成してください。\n"
        "\n"
        "## 解説の構成\n"
        "1. 局面の概要: 手番を述べ、評価値・駒得・玉安全度・囲い・戦法・駒の働きを取り上げる\n"
        "2. 変化手順に触れ、このように指すとこのように対応され、その場合形勢はこうなるという説明をする。\n"
        "- 持ち駒・王の安全・攻め筋/受け筋の観点を優先する\n"
        + style_section +
        "\n"
        "## 制約\n"
        "- 出力は日本語のみ\n"
        "- 箇条書きや見出しは使わず、段落で構成された文章で説明する\n"
        "- 変化手順を説明する際は「▲２四歩△同歩▲２四飛」のように具体的に\n"
        "- 定性的な表現を使い、数値は使わない。\n"
        "- 出力文字数はおおむね指定範囲に収める\n"
        "\n"
        "## 禁止\n"
        "- 入力に存在しない手順の捏造\n"
    )

    examples_text = ""
    if rag_examples:
        blocks: list[str] = []
        for i, ex in enumerate(rag_examples, start=1):
            # use_full_features=True の場合は features_text_full を使う
            ex_features = ex.features_text_full if use_full_features else ex.features_text
            blocks.append(
                "\n".join(
                    [
                        f"--- 参考例{i} 局面特徴 ---",
                        ex_features,
                        f"--- 参考例{i} 解説 ---",
                        ex.commentary,
                    ]
                )
            )
        examples_text = "\n\n".join(blocks).rstrip() + "\n\n"

    user = (
        "次のタスクを実行してください。\n"
        "- 参考例（局面特徴→解説）を読み、局面特徴と解説の関係を学ぶ\n"
        f"文字数: {min_chars}〜{max_chars}文字目安\n\n"
        f"{examples_text}"
        f"--- 対象局面（局面特徴） ---\n{features_text_without_commentary}\n"
    )
    return system, user

