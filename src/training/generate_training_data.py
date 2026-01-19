# -*- coding: utf-8 -*-
"""
教師データ生成スクリプト

局面(SFEN)+コメントのペアから、局面特徴を抽出してLLM学習用教師データを生成する。

使用方法:
    # 10件のみ処理（テスト用）
    python scripts/generate_training_data.py --limit 10

    # 全件処理
    python scripts/generate_training_data.py

    # シミュレーションなし（静的特徴のみ）
    python scripts/generate_training_data.py --static-only
"""

import argparse
import json
import sys
import time
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.features.extractor import FeatureExtractor
from src.features.models import StaticFeatures, DynamicFeatures
from src.training.training_data_utils import (
    collect_terminal_nodes,
    count_valid_jsonl_lines,
    format_seconds,
    load_commentary_data,
    moves_to_kif_format,
)


def generate_training_data(
    entries: list[dict],
    extractor: FeatureExtractor,
    output_path: Path,
    use_simulation: bool = False,
    limit: int | None = None,
    maia_rating: int = 1500,
    append: bool = False,
) -> dict:
    """
    教師データを生成してJSONLinesファイルに出力する。
    
    Args:
        entries: コメントエントリのリスト
        extractor: 特徴抽出器
        output_path: 出力ファイルパス
        use_simulation: シミュレーションを使用するか
        limit: 処理件数上限（Noneで全件）
        
    Returns:
        統計情報
    """
    stats = {
        'processed': 0,
        'success': 0,
        'errors': 0,
    }

    if limit:
        entries = entries[:limit]
    
    total = len(entries)
    print(f"処理対象: {total}件")

    start_time = time.perf_counter()
    last_report_time = start_time
    
    # シミュレーション使用時はGameSimulatorを初期化
    simulator = None
    if use_simulation:
        try:
            from src.simulation.game_simulator import GameSimulator
            from src.simulation.maia2_wrapper import Maia2Config
            
            maia_config = Maia2Config(
                rating_self=maia_rating,
                rating_oppo=maia_rating,
            )
            
            simulator = GameSimulator(maia2_config=maia_config)
            simulator.connect()
            print("シミュレーターに接続しました")
        except Exception as e:
            print(f"警告: シミュレーター初期化失敗: {e}")
            print("静的特徴のみで処理を続行します")
            use_simulation = False
    
    cancelled = False

    try:
        # 行単位でバッファリングし、Ctrl+Cでも「書けた行」は残りやすくする
        mode = 'a' if append else 'w'
        with open(output_path, mode, encoding='utf-8', buffering=1) as f:
            try:
                for i, entry in enumerate(entries):
                    # 進捗表示（完了件数/経過/ETA）: 30秒ごと（＋開始直後）
                    now = time.perf_counter()
                    if i == 0 or (now - last_report_time) >= 30.0:
                        elapsed = now - start_time
                        avg_per_item = (elapsed / (i + 1)) if (i + 1) > 0 else 0.0
                        eta = avg_per_item * (total - (i + 1))
                        print(
                            f"進捗: {i + 1}/{total} | 完了: {stats['success']} | エラー: {stats['errors']} | "
                            f"経過: {format_seconds(elapsed)} | 1件平均: {avg_per_item:.2f}秒 | ETA: {format_seconds(eta)}",
                            flush=True,
                        )
                        last_report_time = now

                    stats['processed'] += 1

                    try:
                        sfen = entry['sfen']

                        # 静的特徴を抽出
                        static_features = extractor.extract_static(sfen)
                        static_text = extractor.to_text(static_features)

                        # シミュレーション結果
                        terminal_features_texts: list[str] = []
                        simulation_info = None

                        if use_simulation and simulator:
                            try:
                                # シミュレーションを実行
                                sim_result = simulator.simulate(sfen)

                                # 全末端局面を収集
                                terminal_nodes = []

                                # best_lineから末端局面
                                if sim_result.best_line:
                                    best_moves = [m.move for m in sim_result.best_line]
                                    best_terminal = {
                                        'sfen': sim_result.best_line[-1].sfen,
                                        'moves': best_moves,
                                        'score': sim_result.best_line[-1].score,
                                        'type': 'best_line',
                                    }
                                    terminal_nodes.append(best_terminal)

                                # TreeNodeから末端局面
                                if sim_result.tree:
                                    tree_terminals = collect_terminal_nodes(sim_result.tree)
                                    for t in tree_terminals:
                                        t['type'] = 'tree'
                                    terminal_nodes.extend(tree_terminals)

                                # 変化前のやねうら王スコアを取得
                                before_yaneuraou_score = sim_result.root_score

                                # 各末端局面について動的特徴を計算
                                for terminal in terminal_nodes:
                                    try:
                                        # 手順をKIF形式に変換
                                        if terminal['moves']:
                                            kif_moves = moves_to_kif_format(terminal['moves'], sfen)
                                        else:
                                            kif_moves = None

                                        # 動的特徴を計算
                                        dynamic = extractor.extract_dynamic(
                                            sfen,
                                            terminal['sfen'],
                                            terminal['moves'] if terminal['moves'] else None
                                        )
                                        # moves_betweenをKIF形式に上書き
                                        if kif_moves:
                                            dynamic.moves_between = kif_moves.split(" → ")

                                        dynamic_text = extractor.to_text(dynamic)

                                        # やねうら王スコアで末端評価値と評価値変化を上書き
                                        yaneuraou_score = terminal.get('score')
                                        if yaneuraou_score is not None and before_yaneuraou_score is not None:
                                            score_change = yaneuraou_score - before_yaneuraou_score
                                            direction = "先手有利に" if score_change > 0 else "後手有利に" if score_change < 0 else ""

                                            lines = dynamic_text.split('\n')
                                            new_lines = []
                                            for line in lines:
                                                if '末端評価値:' in line:
                                                    new_lines.append(f"  末端評価値: {yaneuraou_score:+d}")
                                                elif '評価値変化:' in line:
                                                    new_lines.append(f"  評価値変化: {abs(score_change)} {direction}")
                                                else:
                                                    new_lines.append(line)
                                            dynamic_text = '\n'.join(new_lines)

                                        terminal_features_texts.append(dynamic_text)
                                    except Exception:
                                        pass  # この末端局面はスキップ

                                # シミュレーション情報
                                simulation_info = {
                                    'terminal_count': len(terminal_nodes),
                                    'best_line_length': len(sim_result.best_line) if sim_result.best_line else 0,
                                    'before_score': before_yaneuraou_score,
                                }
                            except Exception as e:
                                print(f"  シミュレーションエラー ({entry['source_file']}): {e}")

                        # 出力テキストを構築
                        output_lines = []

                        # 1. 変化前の局面（静的特徴）
                        output_lines.append("=" * 50)
                        output_lines.append("【変化前の局面】")
                        output_lines.append("=" * 50)
                        output_lines.append(static_text)

                        # 2. シミュレーション結果（各末端局面の動的特徴）
                        if terminal_features_texts:
                            output_lines.append("")
                            output_lines.append("=" * 50)
                            output_lines.append("【シミュレーション結果】")
                            output_lines.append("=" * 50)
                            for idx, term_text in enumerate(terminal_features_texts, 1):
                                output_lines.append(f"\n--- 末端局面{idx} ---")
                                output_lines.append(term_text)

                        # 3. 解説文（最後に配置）
                        output_lines.append("")
                        output_lines.append("=" * 50)
                        output_lines.append("【解説文】")
                        output_lines.append("=" * 50)
                        output_lines.append(entry['comment'])

                        features_text = "\n".join(output_lines)

                        # 出力レコードを作成
                        record = {
                            'sfen': sfen,
                            'features_text': features_text,
                            'commentary': entry['comment'],
                            'source_file': entry.get('source_file'),
                        }

                        # シミュレーション情報があれば追加
                        if simulation_info:
                            record['simulation'] = simulation_info

                        # JSONLines形式で書き込み
                        f.write(json.dumps(record, ensure_ascii=False) + '\n')
                        stats['success'] += 1

                    except Exception as e:
                        stats['errors'] += 1
                        if stats['errors'] <= 5:
                            print(f"  エラー ({entry.get('source_file')}): {e}")

                    # 1件処理後にも、30秒経過していれば進捗を出す（重い1件の直後に出やすくする）
                    now = time.perf_counter()
                    if (now - last_report_time) >= 30.0:
                        done = stats['success'] + stats['errors']
                        elapsed = now - start_time
                        avg_per_item = (elapsed / done) if done > 0 else 0.0
                        eta = avg_per_item * (total - done)
                        print(
                            f"進捗: {done}/{total} | 完了: {stats['success']} | エラー: {stats['errors']} | "
                            f"経過: {format_seconds(elapsed)} | 1件平均: {avg_per_item:.2f}秒 | ETA: {format_seconds(eta)}",
                            flush=True,
                        )
                        last_report_time = now

            except KeyboardInterrupt:
                cancelled = True
                print("\nCtrl+Cを受け取りました。ここまでに生成した分は出力ファイルに残したまま終了します...", flush=True)

            # 最終進捗（サマリ）
            end_time = time.perf_counter()
            elapsed = end_time - start_time
            done = stats['success'] + stats['errors']
            avg_per_item = (elapsed / done) if done > 0 else 0.0
            print(
                f"進捗: {done}/{total} | 完了: {stats['success']} | エラー: {stats['errors']} | "
                f"経過: {format_seconds(elapsed)} | 1件平均: {avg_per_item:.2f}秒" + (" | 中断" if cancelled else ""),
                flush=True,
            )
    
    finally:
        if simulator:
            simulator.disconnect()
            print("シミュレーターを切断しました")
    
    return stats


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(description='教師データ生成')
    parser.add_argument(
        '--limit', type=int, default=None,
        help='処理件数上限（テスト用）'
    )
    parser.add_argument(
        '--static-only', action='store_true',
        help='シミュレーションを使用せず静的特徴のみ抽出'
    )
    parser.add_argument(
        '--output', type=str, default='data/training/training_data.jsonl',
        help='出力ファイルパス'
    )
    parser.add_argument(
        '--resume', action='store_true',
        help='既存のJSONL出力がある場合、続きから追記して再開する'
    )
    parser.add_argument(
        '--overwrite', action='store_true',
        help='既存の出力ファイルがあっても上書きする（注意）'
    )
    parser.add_argument(
        '--min-length', type=int, default=0,
        help='コメントの最小文字数'
    )
    parser.add_argument(
        '--estimate', action='store_true',
        help='実行前に所要時間を概算して終了（出力はしない）'
    )
    parser.add_argument(
        '--estimate-samples', type=int, default=10,
        help='--estimate 時に計測するサンプル件数（デフォルト: 10）'
    )
    parser.add_argument(
        '--maia-rating', type=int, default=1000,
        help='Maia2のレーティング設定（デフォルト: 1000）'
    )
    args = parser.parse_args()
    
    # パスの設定
    base_dir = Path(__file__).parent.parent
    input_dir = base_dir / 'data' / 'kif_commentary_json'
    output_path = base_dir / args.output
    
    # 出力ディレクトリの作成
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("=" * 50)
    print("教師データ生成スクリプト")
    print("=" * 50)
    print(f"入力ディレクトリ: {input_dir}")
    print(f"出力ファイル: {output_path}")
    print(f"シミュレーション: {'なし (静的特徴のみ)' if args.static_only else 'あり'}")
    if args.limit:
        print(f"処理件数上限: {args.limit}")
    print()
    
    # コメントデータを読み込み
    print("コメントデータを読み込み中...")
    entries = load_commentary_data(input_dir, args.min_length)
    print(f"読み込み完了: {len(entries)}件")
    print()

    # 既存出力の扱い（再開/上書き）
    already_done = 0
    append = False
    if output_path.exists():
        if args.overwrite:
            print("警告: --overwrite が指定されたため、既存ファイルを上書きします")
        elif args.resume:
            already_done = count_valid_jsonl_lines(output_path)
            if already_done > 0:
                print(f"再開モード: 既存の有効行数 {already_done} 行を検出。続きから追記します")
                entries = entries[already_done:]
                append = True
            else:
                print("再開モード: 既存ファイルはあるが有効行が0行のため、追記で先頭から生成します")
                append = True
        else:
            raise FileExistsError(
                f"出力ファイルが既に存在します: {output_path}\n"
                "続きから生成する場合は --resume、上書きする場合は --overwrite を指定してください。"
            )

    if args.estimate:
        # 事前見積もり（サンプルを実行して平均時間を推定）
        total = len(entries)
        sample_n = min(args.estimate_samples, total)
        print("=" * 50)
        print("所要時間の概算")
        print("=" * 50)
        print(f"対象件数: {total}件（min-length={args.min_length}）")
        print(f"サンプル計測: {sample_n}件")
        print(f"シミュレーション: {'なし (静的特徴のみ)' if args.static_only else 'あり'}")
        print()

        if sample_n == 0:
            print("対象が0件のため終了します")
            return

        # 特徴抽出器を初期化（GPU使用）
        print("特徴抽出器を初期化中...")
        extractor = FeatureExtractor()
        print("初期化完了")
        print()

        # サンプル実行（ファイル出力なし）
        start = time.perf_counter()
        tmp_out = base_dir / 'data' / 'training' / '_estimate_tmp.jsonl'
        tmp_out.parent.mkdir(parents=True, exist_ok=True)
        generate_training_data(
            entries=entries,
            extractor=extractor,
            output_path=tmp_out,
            use_simulation=not args.static_only,
            limit=sample_n,
            maia_rating=args.maia_rating,
            append=False,
        )
        elapsed = time.perf_counter() - start
        avg = elapsed / sample_n
        est_total = avg * total
        print()
        print("--- 概算結果 ---")
        print(f"サンプル合計: {elapsed:.1f}秒 / {sample_n}件")
        print(f"1件平均: {avg:.2f}秒")
        print(f"全体推定: {est_total/60.0:.1f}分（約{est_total/3600.0:.2f}時間）")
        print("※局面やエンジン負荷でブレます。シミュレーションありだと特に変動します。")
        return
    
    # 特徴抽出器を初期化（GPU使用）
    print("特徴抽出器を初期化中...")
    extractor = FeatureExtractor()
    print("初期化完了")
    print()
    
    # 教師データを生成
    print("教師データを生成中...")
    stats = generate_training_data(
        entries=entries,
        extractor=extractor,
        output_path=output_path,
        use_simulation=not args.static_only,
        limit=args.limit,
        maia_rating=args.maia_rating,
        append=append,
    )
    
    # 結果表示
    print()
    print("=" * 50)
    print("生成完了")
    print("=" * 50)
    print(f"処理件数: {stats['processed']}")
    print(f"成功: {stats['success']}")
    print(f"エラー: {stats['errors']}")
    print(f"出力ファイル: {output_path}")


if __name__ == '__main__':
    main()
