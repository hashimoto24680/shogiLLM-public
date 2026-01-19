# -*- coding: utf-8 -*-
"""
シミュレーションツリー出力スクリプト

5パターンの局面からツリーを構築し、構造と勝率をファイルに出力する。
棋譜表記、ルート局面・終端局面の盤面、KIF形式の変化手順も表示。
"""

from datetime import datetime
import cshogi
from cshogi import KI2
from src.simulation.game_simulator import GameSimulator
from src.simulation.maia2_wrapper import Maia2Config
from src.simulation.models import TreeNode, MoveRecord


# テスト局面
POSITIONS = {
    "パターン0_初期局面_互角": "lnsgkgsnl/1r5b1/ppppppppp/9/9/9/PPPPPPPPP/1B5R1/LNSGKGSNL b - 1",
    "パターン1_角換わり中盤_後手不利": "ln1g3nl/1rs2kg2/p2ppp1pp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L w B2Pb 28",
    "パターン2_角換わり中盤2_先手有利": "ln1g4l/1rs2kg2/p2pppnpp/2p2sR2/1p3N3/2P2PP2/PPSPP3P/5S3/LN1GKG2L b B2Pb 29",
    "パターン3_棒銀終盤2_後手有利": "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/3S3R1/L3KG1NL w BSPbgnp 30",
    "パターン4_棒銀終盤_先手不利": "ln1gk2nl/6gs1/p1pppp1pp/6p2/7P1/P1P2SP2/2+rPPP2P/7R1/L1S1KG1NL b BSPbgnp 29",
}


def sfen_to_bod(sfen: str) -> str:
    """SFENをBOD形式（日本語盤面表記）に変換する。"""
    board = cshogi.Board()
    board.set_sfen(sfen)
    return board.to_bod()


def sfen_to_board_str(sfen: str) -> str:
    """SFENをCSA形式の盤面文字列に変換する。"""
    board = cshogi.Board()
    board.set_sfen(sfen)
    return str(board)


def usi_to_ki2(usi_move: str, parent_sfen: str) -> str:
    """
    USI形式の指し手を棋譜表記に変換する。
    
    Args:
        usi_move: USI形式の指し手（例: "7g7f"）
        parent_sfen: 親局面のSFEN（指し手を指す前の局面）
        
    Returns:
        棋譜表記（例: "▲７六歩"）
    """
    board = cshogi.Board()
    board.set_sfen(parent_sfen)
    
    # USI形式からmove_intに変換（boardのメソッドを使用）
    move = board.move_from_usi(usi_move)
    
    # 合法手かチェック（不正な手の場合はUSI形式をそのまま返す）
    if move is None or move not in board.legal_moves:
        return usi_move
    
    return KI2.move_to_ki2(move, board)


def usi_to_ki2_short(usi_move: str, parent_sfen: str) -> str:
    """
    USI形式の指し手を短い棋譜表記に変換する（▲△なし）。
    """
    ki2 = usi_to_ki2(usi_move, parent_sfen)
    # ▲△を除去
    if ki2.startswith("▲") or ki2.startswith("△"):
        return ki2[1:]
    return ki2


def best_line_to_ki2(best_line: list[MoveRecord], root_sfen: str) -> list[str]:
    """最善応酬をKI2形式のリストに変換する。"""
    ki2_moves = []
    board = cshogi.Board()
    board.set_sfen(root_sfen)
    
    for record in best_line:
        move = board.move_from_usi(record.move)
        if move:
            ki2 = KI2.move_to_ki2(move, board)
            ki2_moves.append(ki2)
            board.push(move)
    
    return ki2_moves


def collect_terminal_nodes(node: TreeNode) -> list[TreeNode]:
    """終端ノードを収集する。"""
    terminals = []
    if node.is_terminal:
        terminals.append(node)
    for child in node.children:
        terminals.extend(collect_terminal_nodes(child))
    return terminals


def format_tree_node(node: TreeNode, indent: int = 0, parent_sfen: str | None = None) -> str:
    """
    ツリーノードを文字列にフォーマットする（再帰）。
    """
    prefix = "  " * indent
    
    # ノード情報
    if node.move and parent_sfen:
        ki2_move = usi_to_ki2(node.move, parent_sfen)
        move_str = f"[{ki2_move}]"
    elif node.move:
        move_str = f"[{node.move}]"
    else:
        move_str = "[ルート]"
    
    # 終端マーク
    terminal_mark = " ★終端" if node.is_terminal else ""
    
    line = f"{prefix}{move_str} 深さ{node.depth} | 強AI: {node.strong_eval_win_rate:.1%} | 弱AI: {node.weak_eval_win_rate:.1%}{terminal_mark}\n"
    
    # 子ノードを再帰的に処理（現在のノードのSFENを親SFENとして渡す）
    for child in node.children:
        line += format_tree_node(child, indent + 1, node.sfen)
    
    return line


def count_nodes(node: TreeNode) -> int:
    """ノード数をカウントする。"""
    count = 1
    for child in node.children:
        count += count_nodes(child)
    return count


def collect_all_paths(node: TreeNode, current_path: list, all_paths: list, parent_sfen: str | None = None):
    """
    ツリーから全ての変化手順を収集する。
    各パスは [(move_ki2, node), ...] のリスト。
    """
    if node.move and parent_sfen:
        ki2 = usi_to_ki2(node.move, parent_sfen)
        current_path = current_path + [(ki2, node)]
    else:
        current_path = [(None, node)]  # ルート
    
    if node.is_terminal or not node.children:
        # 終端またはリーフに到達
        all_paths.append(current_path)
    else:
        for child in node.children:
            collect_all_paths(child, current_path, all_paths, node.sfen)


def format_kif_variations(tree: TreeNode, root_sfen: str) -> str:
    """
    ツリーをKIF形式の変化手順にフォーマットする。
    
    出力例:
    △２五角    ▲４四飛    △同　歩    ▲５五角
    
    変化：3手目
    △７三桂
    """
    all_paths = []
    collect_all_paths(tree, [], all_paths)
    
    if not all_paths:
        return ""
    
    # 最初のパス（主手順）
    main_path = all_paths[0]
    
    lines = [""]  # BOD形式と手順の間に空行を入れる
    
    # 主手順を出力（ルートをスキップ）
    main_moves = [ki2 for ki2, node in main_path if ki2 is not None]
    if main_moves:
        # 8手ずつで改行
        for i in range(0, len(main_moves), 8):
            chunk = main_moves[i:i+8]
            lines.append("    ".join(chunk))
    
    # 変化手順を出力
    for path in all_paths[1:]:
        # 主手順との分岐点を探す
        moves = [(ki2, node) for ki2, node in path if ki2 is not None]
        
        # 分岐点を特定（深さで判断）
        if moves:
            first_move_ki2, first_node = moves[0]
            branch_depth = first_node.depth
            
            lines.append("")
            lines.append(f"変化：{branch_depth}手目")
            
            variation_moves = [ki2 for ki2, node in moves]
            for i in range(0, len(variation_moves), 8):
                chunk = variation_moves[i:i+8]
                lines.append("    ".join(chunk))
    
    return "\n".join(lines)


def main():
    """メイン処理。"""
    output_path = "docs/simulation_tree_output.md"
    
    maia2_config = Maia2Config(rating_self=2700, rating_oppo=2700)
    
    with open(output_path, "w", encoding="utf-8") as f:
        f.write("# シミュレーションツリー出力\n\n")
        f.write(f"生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        f.write("---\n\n")
        
        with GameSimulator(maia2_config=maia2_config) as sim:
            for name, sfen in POSITIONS.items():
                print(f"処理中: {name}")
                
                f.write(f"## {name}\n\n")
                f.write(f"**SFEN**: `{sfen}`\n\n")
                
                # 手番の判定
                is_sente = sfen.split()[1] == "b"
                turn_str = "先手番" if is_sente else "後手番"
                f.write(f"**手番**: {turn_str}\n\n")
                
                # ルート局面の盤面表示
                f.write("### ルート局面\n\n")
                f.write("```\n")
                f.write(sfen_to_board_str(sfen))
                f.write("```\n\n")
                
                # シミュレーション実行
                result = sim.simulate(sfen)
                
                # 最善応酬（棋譜形式）
                f.write("### 最善応酬（強AI vs 強AI）\n\n")
                
                ki2_moves = best_line_to_ki2(result.best_line, sfen)
                f.write("| 手数 | 指し手 | 評価値 | 手番側勝率 |\n")
                f.write("|------|--------|--------|------------|\n")
                for i, (record, ki2) in enumerate(zip(result.best_line, ki2_moves), 1):
                    # 手番側勝率（先手番なら先手視点、後手番なら後手視点）
                    # やねうら王の勝率は手番側視点なのでそのまま使用
                    turn_wr = record.win_rate
                    f.write(f"| {i} | {ki2} | {record.score:+d} | {turn_wr:.1%} |\n")
                f.write("\n")
                
                # 最善応酬の最終局面
                if result.best_line:
                    f.write("#### 最善応酬の最終局面\n\n")
                    board = cshogi.Board()
                    board.set_sfen(sfen)
                    for record in result.best_line:
                        move = board.move_from_usi(record.move)
                        if move:
                            board.push(move)
                    f.write("```\n")
                    f.write(str(board))
                    f.write("\n```\n\n")
                
                # ツリー構造
                f.write("### ツリー構造（弱AI vs 強AI）\n\n")
                f.write(f"**ノード数**: {count_nodes(result.tree)}\n\n")
                f.write("```\n")
                f.write(format_tree_node(result.tree))
                f.write("```\n\n")
                
                # KIF形式の変化手順
                f.write("### KIF形式の変化手順\n\n")
                f.write("```\n")
                f.write(sfen_to_bod(sfen))
                f.write(format_kif_variations(result.tree, sfen))
                f.write("\n```\n\n")
                
                # KI2Uファイル独立出力
                ki2u_path = f"docs/simulation_{name}.ki2u"
                with open(ki2u_path, "w", encoding="utf-8") as ki2u_file:
                    ki2u_file.write(sfen_to_bod(sfen))
                    ki2u_file.write(format_kif_variations(result.tree, sfen))
                    ki2u_file.write("\n")
                print(f"  -> KI2U出力: {ki2u_path}")
                
                # 終端局面の盤面表示
                terminals = collect_terminal_nodes(result.tree)
                if terminals:
                    f.write("### 終端局面一覧\n\n")
                    for i, term in enumerate(terminals, 1):
                        f.write(f"#### 終端{i}: 強AI {term.strong_eval_win_rate:.1%} / 弱AI {term.weak_eval_win_rate:.1%}\n\n")
                        f.write("```\n")
                        f.write(sfen_to_bod(term.sfen))
                        f.write("```\n\n")
                
                f.write("---\n\n")
                
                print(f"  -> 完了（ノード数: {count_nodes(result.tree)}, 終端: {len(terminals)}）")
    
    print(f"\n出力完了: {output_path}")


if __name__ == "__main__":
    main()
