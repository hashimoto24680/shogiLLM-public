# -*- coding: utf-8 -*-
r"""OpenAI APIで将棋の解説文（コメント）を生成する。

入力:
    JSONL（1行=1レコード）
    - 想定キー: features_text, sfen, commentary（既存の解説）, source_file, simulation

出力:
    JSONL（入力レコードに generated_commentary 等を付与）

方針:
    - features_text 末尾の「【解説文】」以降は教師データ（正解）なのでプロンプトに含めない
    - 途中でCtrl+Cしても、書けた行は残る
    - --resume で出力JSONLの行数分だけスキップして続きから再開

環境変数:
    - OPENAI_API_KEY: 必須
    - OPENAI_MODEL: 任意（例: gpt-4.1-mini）

例:
    .\.venv\Scripts\python.exe scripts\generate_commentary_openai.py --input data\training\part1.jsonl --output data\training\part1_generated.jsonl --min-chars 100 --max-chars 220 --resume
"""

from __future__ import annotations

import argparse
import json
import os
import random
import time
from dataclasses import dataclass
from pathlib import Path


def _truncate(text: str, max_chars: int) -> str:
    if max_chars <= 0:
        return ""
    if len(text) <= max_chars:
        return text
    return text[: max_chars - 1].rstrip() + "…"


def _fmt_seconds(seconds: float) -> str:
    seconds = max(0.0, float(seconds))
    m, s = divmod(int(seconds + 0.5), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h:d}時間{m:02d}分{s:02d}秒"
    if m:
        return f"{m:d}分{s:02d}秒"
    return f"{s:d}秒"


def _strip_teacher_commentary(features_text: str) -> str:
    """features_text から教師の解説文セクションを除去する。"""
    marker = "【解説文】"
    idx = features_text.find(marker)
    if idx == -1:
        return features_text
    return features_text[:idx].rstrip()


def _has_teacher_commentary_in_features(features_text: str) -> bool:
    """features_text 内に教師解説（【解説文】以降の非空テキスト）が含まれるか。"""
    marker = "【解説文】"
    idx = features_text.find(marker)
    if idx == -1:
        return False
    tail = features_text[idx + len(marker) :]
    return bool(tail.strip())


# _compact_features_text は commentary_openai_helpers から使用
from src.training.commentary_openai_helpers import compact_features_text as _compact_features_text


def count_valid_jsonl_lines(path: Path) -> int:
    if not path.exists():
        return 0
    count = 0
    with open(path, 'r', encoding='utf-8') as rf:
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


@dataclass
class OpenAIConfig:
    model: str
    temperature: float
    max_output_tokens: int


# make_prompt は commentary_openai_helpers から使用
from src.training.commentary_openai_helpers import make_prompt


def get_openai_client():
    """openai>=1.x を想定。"""
    try:
        from openai import OpenAI  # type: ignore
    except Exception as e:
        raise ImportError(
            "openai パッケージが見つかりません。requirementsのopenaiを .venv にインストールしてください。"
        ) from e

    return OpenAI()


def call_openai(system: str, user: str, cfg: OpenAIConfig) -> tuple[str, dict]:
    client = get_openai_client()

    # 互換性重視: responses API
    resp = client.responses.create(
        model=cfg.model,
        input=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=cfg.temperature,
        max_output_tokens=cfg.max_output_tokens,
    )

    text = (resp.output_text or "").strip()
    meta = {
        "id": getattr(resp, "id", None),
        "model": cfg.model,
    }
    return text, meta


def _embed_texts(texts: list[str], embedding_model: str) -> list[list[float]]:
    """OpenAI embeddings をまとめて取得する。"""
    client = get_openai_client()
    resp = client.embeddings.create(
        model=embedding_model,
        input=texts,
    )
    data = list(getattr(resp, "data", []) or [])
    data.sort(key=lambda d: getattr(d, "index", 0))
    return [list(d.embedding) for d in data]


@dataclass
class RagConfig:
    enabled: bool
    examples_jsonl: Path | None
    index_base: Path | None
    embedding_model: str
    top_k: int
    max_feature_chars: int
    max_example_commentary_chars: int
    batch_size: int
    progress_every: int


@dataclass
class RagExample:
    sfen: str
    features_text: str
    features_text_full: str
    commentary: str
    source_file: str | None


def _rag_paths(index_base: Path) -> tuple[Path, Path, Path]:
    # base を "idx" などにしておけば、idx.npz / idx.meta.jsonl / idx.info.json ができる
    return (
        index_base.with_suffix(index_base.suffix + ".npz"),
        index_base.with_suffix(index_base.suffix + ".meta.jsonl"),
        index_base.with_suffix(index_base.suffix + ".info.json"),
    )


def build_rag_index(
    examples_jsonl: Path,
    index_base: Path,
    embedding_model: str,
    max_feature_chars: int,
    max_example_commentary_chars: int,
    batch_size: int,
    resume: bool,
    progress_every: int,
) -> None:
    """教師データJSONLから埋め込みインデックスを作る。"""

    import numpy as np  # 遅延import

    npz_path, meta_path, info_path = _rag_paths(index_base)
    index_base.parent.mkdir(parents=True, exist_ok=True)

    total_lines = count_valid_jsonl_lines(examples_jsonl)
    existing_embeddings: np.ndarray | None = None
    start = 0
    if resume and npz_path.exists() and meta_path.exists():
        try:
            with np.load(npz_path) as z:
                existing_embeddings = z["embeddings"].astype(np.float32)
            start = count_valid_jsonl_lines(meta_path)
            if existing_embeddings.shape[0] != start:
                raise ValueError(
                    f"既存インデックスが不整合です: embeddings={existing_embeddings.shape[0]}, meta_lines={start}"
                )
            print(f"RAGインデックス再開: 既存 {start} 件を検出。追記します", flush=True)
        except Exception:
            existing_embeddings = None
            start = 0
            print("RAGインデックス再開に失敗したため、最初から作り直します", flush=True)

    embeddings_chunks: list[np.ndarray] = []
    written = 0
    batch_texts: list[str] = []
    batch_meta: list[dict] = []
    last_report = start
    start_time = time.time()

    def flush_batch() -> None:
        nonlocal written, batch_texts, batch_meta, last_report, start_time
        if not batch_texts:
            return
        vectors = _embed_texts(batch_texts, embedding_model=embedding_model)
        arr = np.asarray(vectors, dtype=np.float32)
        norms = np.linalg.norm(arr, axis=1, keepdims=True)
        arr = arr / np.maximum(norms, 1e-12)
        embeddings_chunks.append(arr)

        # metaは追記（1行=1例、embeddingsと行番号が一致）
        meta_mode = "a" if (start > 0 or written > 0) else "w"
        with open(meta_path, meta_mode, encoding="utf-8", buffering=1) as wf:
            for m in batch_meta:
                wf.write(json.dumps(m, ensure_ascii=False) + "\n")

        written += len(batch_texts)
        if progress_every > 0:
            total_done = start + written
            if total_done - last_report >= progress_every:
                elapsed = max(1e-6, time.time() - start_time)
                done_since_start = max(1, total_done - start)
                rate = done_since_start / elapsed
                remaining = max(0, total_lines - total_done)
                eta = remaining / rate if rate > 0 else 0
                pct = (total_done / total_lines * 100.0) if total_lines > 0 else 0.0
                print(
                    f"RAG進捗: {total_done}/{total_lines} ({pct:.1f}%) | "
                    f"{_fmt_seconds(elapsed)} 経過 | 残り { _fmt_seconds(eta) }",
                    flush=True,
                )
                last_report = total_done
        batch_texts = []
        batch_meta = []

    with open(examples_jsonl, "r", encoding="utf-8") as rf:
        for i, line in enumerate(rf):
            if i < start:
                continue
            raw = line.strip()
            if not raw:
                continue
            try:
                rec = json.loads(raw)
            except Exception:
                continue

            features_text = rec.get("features_text", "")
            commentary = rec.get("commentary", "")
            if not features_text or not commentary:
                continue

            # 教師解説を除去したフルテキスト
            features_text_full = _strip_teacher_commentary(features_text)
            # 埋め込み用に短縮
            compact = _compact_features_text(features_text, max_chars=max_feature_chars)
            if not compact:
                continue

            batch_texts.append(compact)
            batch_meta.append(
                {
                    "sfen": rec.get("sfen", ""),
                    "features_text": compact,
                    "features_text_full": features_text_full,
                    "commentary": _truncate(str(commentary), max_example_commentary_chars),
                    "source_file": rec.get("source_file"),
                }
            )

            if len(batch_texts) >= batch_size:
                flush_batch()

    flush_batch()

    if existing_embeddings is not None:
        new_emb = (
            np.concatenate(embeddings_chunks, axis=0)
            if embeddings_chunks
            else np.empty((0, existing_embeddings.shape[1]), dtype=np.float32)
        )
        embeddings = np.concatenate([existing_embeddings, new_emb], axis=0)
    else:
        embeddings = np.concatenate(embeddings_chunks, axis=0) if embeddings_chunks else None

    if embeddings is None or embeddings.shape[0] == 0:
        raise RuntimeError("RAGインデックスを作れませんでした（有効データ0件）")

    np.savez_compressed(npz_path, embeddings=embeddings)
    info = {
        "embedding_model": embedding_model,
        "count": int(embeddings.shape[0]),
        "dim": int(embeddings.shape[1]),
        "max_feature_chars": max_feature_chars,
        "max_example_commentary_chars": max_example_commentary_chars,
        "source_jsonl": str(examples_jsonl),
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    with open(info_path, "w", encoding="utf-8") as wf:
        wf.write(json.dumps(info, ensure_ascii=False, indent=2))

    print(f"RAGインデックス作成完了: {embeddings.shape[0]}件 (dim={embeddings.shape[1]})", flush=True)


def load_rag_index(index_base: Path):
    import numpy as np  # 遅延import

    npz_path, meta_path, _info_path = _rag_paths(index_base)
    if not npz_path.exists() or not meta_path.exists():
        raise FileNotFoundError(f"RAGインデックスが見つかりません: {npz_path} / {meta_path}")

    with np.load(npz_path) as z:
        embeddings = z["embeddings"].astype(np.float32)

    examples: list[RagExample] = []
    with open(meta_path, "r", encoding="utf-8") as rf:
        for line in rf:
            raw = line.strip()
            if not raw:
                continue
            try:
                m = json.loads(raw)
            except Exception:
                continue
            examples.append(
                RagExample(
                    sfen=str(m.get("sfen", "")),
                    features_text=str(m.get("features_text", "")),
                    features_text_full=str(m.get("features_text_full", m.get("features_text", ""))),
                    commentary=str(m.get("commentary", "")),
                    source_file=m.get("source_file"),
                )
            )

    if embeddings.shape[0] != len(examples):
        raise ValueError(f"RAGインデックス不整合: embeddings={embeddings.shape[0]}, meta={len(examples)}")

    return embeddings, examples


def retrieve_rag_examples(
    query_features_text: str,
    embeddings,
    examples: list[RagExample],
    embedding_model: str,
    top_k: int,
    exclude_sfen: str | None,
) -> list[RagExample]:
    import numpy as np  # 遅延import

    vec = _embed_texts([query_features_text], embedding_model=embedding_model)[0]
    q = np.asarray(vec, dtype=np.float32)
    q = q / max(float(np.linalg.norm(q)), 1e-12)
    sims = embeddings @ q

    k = max(0, int(top_k))
    if k <= 0:
        return []
    k = min(k, int(sims.shape[0]))

    idxs = np.argpartition(sims, -k)[-k:]
    idxs = idxs[np.argsort(-sims[idxs])]

    out: list[RagExample] = []
    for ix in idxs.tolist():
        ex = examples[ix]
        if exclude_sfen and ex.sfen and ex.sfen == exclude_sfen:
            continue
        out.append(ex)
        if len(out) >= k:
            break
    return out


def _moves_to_kif_format(moves: list[str], start_sfen: str) -> str:
    """USI形式の手順をKIF形式に変換する。"""
    import cshogi
    import sys
    from pathlib import Path as _Path
    sys.path.insert(0, str(_Path(__file__).parent.parent))
    from src.utils.KIF_to_usi import usi_move_to_kif

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
            except:
                break

    return " → ".join(kif_moves)


def extract_features_text_from_sfen(sfen: str, use_simulation: bool = True) -> str:
    """SFENから features_text を生成する（generate_training_data と同等のパイプライン）。"""
    import sys
    from pathlib import Path as _Path

    sys.path.insert(0, str(_Path(__file__).parent.parent))
    from src.features.extractor import FeatureExtractor

    extractor = FeatureExtractor()
    static_features = extractor.extract_static(sfen)
    static_text = extractor.to_text(static_features)

    terminal_features_texts: list[str] = []
    simulation_info = None
    best_line_included = False

    if use_simulation:
        try:
            from src.simulation.game_simulator import GameSimulator
            from src.simulation.maia2_wrapper import Maia2Config

            maia_config = Maia2Config(rating_self=1500, rating_oppo=1500)
            simulator = GameSimulator(maia2_config=maia_config)
            simulator.connect()

            sim_result = simulator.simulate(sfen)

            def _win_rate_to_score(win_rate: float) -> int:
                import math
                if win_rate <= 0.001:
                    return -10000
                if win_rate >= 0.999:
                    return 10000
                return int(-600 * math.log((1.0 / win_rate) - 1))

            def _collect_terminal_nodes(node, path=None):
                if path is None:
                    path = []
                terminals = []
                current_path = path + ([node.move] if node.move else [])
                if node.is_terminal or not node.children:
                    return [
                        {
                            "sfen": node.sfen,
                            "moves": current_path,
                            "score": _win_rate_to_score(node.strong_eval_win_rate),
                        }
                    ]
                for child in node.children:
                    terminals.extend(_collect_terminal_nodes(child, current_path))
                return terminals

            terminal_nodes = []
            if sim_result.best_line:
                best_line_included = True
                best_moves = [m.move for m in sim_result.best_line]
                terminal_nodes.append(
                    {
                        "sfen": sim_result.best_line[-1].sfen,
                        "moves": best_moves,
                        "score": sim_result.best_line[-1].score,
                    }
                )
            if sim_result.tree:
                terminal_nodes.extend(_collect_terminal_nodes(sim_result.tree))

            before_score = sim_result.root_score
            for terminal in terminal_nodes:
                try:
                    # 手順をKIF形式に変換
                    if terminal["moves"]:
                        kif_moves_str = _moves_to_kif_format(terminal["moves"], sfen)
                    else:
                        kif_moves_str = None

                    dynamic = extractor.extract_dynamic(sfen, terminal["sfen"], terminal["moves"])
                    # moves_betweenをKIF形式に上書き
                    if kif_moves_str:
                        dynamic.moves_between = kif_moves_str.split(" → ")
                    dynamic_text = extractor.to_text(dynamic)
                    score = terminal.get("score")
                    if score is not None and before_score is not None:
                        change = score - before_score
                        direction = "先手有利に" if change > 0 else "後手有利に" if change < 0 else ""
                        lines = dynamic_text.split("\n")
                        new_lines = []
                        for line in lines:
                            if "末端評価値:" in line:
                                new_lines.append(f"  末端評価値: {score:+d}")
                            elif "評価値変化:" in line:
                                new_lines.append(f"  評価値変化: {abs(change)} {direction}")
                            else:
                                new_lines.append(line)
                        dynamic_text = "\n".join(new_lines)
                    terminal_features_texts.append(dynamic_text)
                except Exception:
                    pass

            simulation_info = {
                "terminal_count": len(terminal_nodes),
                "best_line_length": len(sim_result.best_line) if sim_result.best_line else 0,
                "before_score": before_score,
            }
            # 静的特徴の評価値をやねうら王のroot_scoreで上書き
            if before_score is not None:
                lines = static_text.split("\n")
                new_lines = []
                for line in lines:
                    if line.strip().startswith("【評価値】"):
                        new_lines.append(f"【評価値】{before_score:+d}")
                    else:
                        new_lines.append(line)
                static_text = "\n".join(new_lines)
        except Exception as e:
            print(f"シミュレーションエラー: {e}", flush=True)

    output_lines = []
    output_lines.append("=" * 50)
    output_lines.append("【変化前の局面】")
    output_lines.append("=" * 50)
    output_lines.append(static_text)

    if terminal_features_texts:
        output_lines.append("")
        output_lines.append("=" * 50)
        output_lines.append("【シミュレーション結果】")
        output_lines.append("=" * 50)
        for idx, term_text in enumerate(terminal_features_texts, 1):
            suffix = "（AIの推奨手順）" if idx == 1 and best_line_included else ""
            output_lines.append(f"\n--- 考えられる変化{idx}{suffix} ---")
            output_lines.append(term_text)

    return "\n".join(output_lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="OpenAIで将棋解説文を生成")
    parser.add_argument("--input", required=False, help="入力JSONL（--sfenと排他）")
    parser.add_argument("--output", required=False, help="出力JSONL（--sfenと排他）")
    parser.add_argument("--sfen", type=str, default=None, help="単一SFENを直接指定（この場合は入出力不要で解説を標準出力に表示）")
    parser.add_argument("--no-simulation", action="store_true", help="--sfen モードでシミュレーションを省略")
    parser.add_argument("--save-features", type=str, default="auto", help="--sfen モードで生成した局面特徴(features_text)を保存するファイルパス（'auto'で自動連番、'none'で無効）")
    parser.add_argument("--save-prompt", type=str, default="auto", help="--sfen モードで使用したプロンプト全文(system+user)を保存するファイルパス（'auto'で自動連番、'none'で無効）")
    parser.add_argument("--resume", action="store_true", help="出力が既にある場合、行数分スキップして追記")
    parser.add_argument("--overwrite", action="store_true", help="出力を上書き")
    parser.add_argument("--limit", type=int, default=None, help="処理件数上限")
    parser.add_argument("--min-chars", type=int, default=500, help="生成解説文の目安最小文字数")
    parser.add_argument("--max-chars", type=int, default=1000, help="生成解説文の目安最大文字数")
    parser.add_argument("--model", type=str, default=os.getenv("OPENAI_MODEL", "gpt-5.2"), help="OpenAIモデル")
    parser.add_argument(
        "--embedding-model",
        type=str,
        default=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        help="RAG用埋め込みモデル",
    )
    parser.add_argument("--temperature", type=float, default=0.7, help="生成温度")
    parser.add_argument("--max-output-tokens", type=int, default=1500, help="最大出力トークン")
    parser.add_argument("--sleep", type=float, default=0.0, help="1リクエストごとの待ち秒")

    # RAG（埋め込み + 類似検索）- デフォルトで有効
    parser.add_argument("--no-rag", action="store_true", help="RAGを無効にする（類似例をプロンプトに含めない）")
    parser.add_argument("--rag-examples", type=str, default=None, help="類似検索に使う教師JSONL（commentary入り）- 未指定時はインデックス既存なら不要")
    parser.add_argument(
        "--rag-index",
        type=str,
        default="data/rag/idx_full",
        help="RAGインデックスのベースパス（デフォルト: data/rag/idx_full）",
    )
    parser.add_argument("--build-rag-index", action="store_true", help="RAGインデックスを作成（無ければ自動作成）")
    parser.add_argument("--build-rag-index-only", action="store_true", help="RAGインデックス作成だけして終了")
    parser.add_argument("--rag-top-k", type=int, default=3, help="RAGで取得する参考例の数")
    parser.add_argument("--rag-max-feature-chars", type=int, default=2000, help="埋め込み/プロンプト用features_text短縮上限")
    parser.add_argument("--rag-max-example-commentary-chars", type=int, default=300, help="参考例の解説文の最大文字数")
    parser.add_argument("--rag-batch-size", type=int, default=64, help="埋め込み作成のバッチサイズ")
    parser.add_argument("--rag-progress-every", type=int, default=1000, help="RAGインデックス作成の進捗表示間隔（件数）")
    parser.add_argument("--rag-no-compact", action="store_true", help="参考例の局面特徴を短縮せずフルでプロンプトに含める")
    
    # スタイル例（解説文の言い回しを学習させる）
    parser.add_argument("--style-examples-count", type=int, default=100, help="スタイル例として読み込む解説文の数（0で無効）")
    parser.add_argument("--style-examples-jsonl", type=str, default="data/training/training_data_filtered.jsonl", help="スタイル例を読み込むJSONLファイル")
    
    parser.add_argument("--skip-if-has-commentary", action="store_true", help="入力にcommentaryがある行は生成をスキップ")
    parser.add_argument(
        "--skip-if-features-has-teacher-commentary",
        action="store_true",
        help="features_text 内に教師解説（【解説文】以降の非空テキスト）がある行は生成をスキップ",
    )
    parser.add_argument(
        "--sanitize-output-features-text",
        action="store_true",
        help="出力JSONLの features_text から【解説文】以降を削除して保存（事故防止）",
    )
    args = parser.parse_args()

    # .env を読む（あれば）
    try:
        from dotenv import load_dotenv  # type: ignore

        load_dotenv()
    except Exception:
        pass

    if not os.getenv("OPENAI_API_KEY"):
        raise EnvironmentError("OPENAI_API_KEY が未設定です。環境変数または .env に設定してください。")

    rag = RagConfig(
        enabled=not args.no_rag,  # デフォルトで有効、--no-ragで無効
        examples_jsonl=Path(args.rag_examples) if args.rag_examples else None,
        index_base=Path(args.rag_index) if args.rag_index else None,
        embedding_model=args.embedding_model,
        top_k=int(args.rag_top_k),
        max_feature_chars=int(args.rag_max_feature_chars),
        max_example_commentary_chars=int(args.rag_max_example_commentary_chars),
        batch_size=int(args.rag_batch_size),
        progress_every=int(args.rag_progress_every),
    )

    rag_embeddings = None
    rag_examples: list[RagExample] | None = None

    if rag.enabled:
        if rag.index_base is None:
            rag.index_base = Path("data/rag/idx_full")
        
        npz_path, meta_path, _info_path = _rag_paths(rag.index_base)
        
        # インデックスが存在しない場合のみ rag_examples が必須
        if not npz_path.exists() or not meta_path.exists():
            if rag.examples_jsonl is None:
                raise ValueError(
                    f"RAGインデックスが見つかりません: {rag.index_base}\n"
                    "インデックスを作成するには --rag-examples（commentary入り教師JSONL）を指定してください。\n"
                    "RAGを無効にするには --no-rag を指定してください。"
                )
        need_build = args.build_rag_index or (not npz_path.exists()) or (not meta_path.exists())
        if need_build:
            build_rag_index(
                examples_jsonl=rag.examples_jsonl,
                index_base=rag.index_base,
                embedding_model=rag.embedding_model,
                max_feature_chars=rag.max_feature_chars,
                max_example_commentary_chars=rag.max_example_commentary_chars,
                batch_size=rag.batch_size,
                resume=args.resume,
                progress_every=rag.progress_every,
            )

        if args.build_rag_index_only:
            print("--build-rag-index-only が指定されたため終了します")
            return

        rag_embeddings, rag_examples = load_rag_index(rag.index_base)
        print(
            f"RAG有効: index={rag.index_base} | embedding_model={rag.embedding_model} | top_k={rag.top_k}",
            flush=True,
        )

    # ────────────────────────────────────────────────────────────────
    # --sfen モード: 単一SFENを直接指定して解説文を標準出力に表示
    # ────────────────────────────────────────────────────────────────
    if args.sfen:
        print("SFENモード: 特徴抽出→RAG→解説生成を一括実行します", flush=True)
        use_sim = not args.no_simulation
        features_text = extract_features_text_from_sfen(args.sfen, use_simulation=use_sim)
        features_wo = _strip_teacher_commentary(features_text)

        rag_selected: list[RagExample] | None = None
        if rag.enabled and rag_embeddings is not None and rag_examples is not None:
            query_compact = _compact_features_text(features_text, max_chars=rag.max_feature_chars)
            rag_selected = retrieve_rag_examples(
                query_features_text=query_compact,
                embeddings=rag_embeddings,
                examples=rag_examples,
                embedding_model=rag.embedding_model,
                top_k=rag.top_k,
                exclude_sfen=args.sfen,
            )
            print(f"RAGで {len(rag_selected)} 件の参考例を取得しました", flush=True)

        # スタイル例を読み込む
        style_examples: list[str] | None = None
        if args.style_examples_count > 0:
            from src.training.commentary_openai_helpers import load_style_examples
            style_examples = load_style_examples(
                Path(args.style_examples_jsonl),
                max_count=args.style_examples_count
            )
            print(f"スタイル例として {len(style_examples)} 件の解説文を読み込みました", flush=True)

        system, user = make_prompt(
            features_wo,
            args.min_chars,
            args.max_chars,
            rag_examples=rag_selected,
            use_full_features=args.rag_no_compact,
            style_examples=style_examples,
        )

        # 中間ファイル出力（自動連番対応）
        def _get_next_versioned_path(base_dir: Path, prefix: str, suffix: str) -> Path:
            """重複しないファイル名を生成（prefix_v1.txt, prefix_v2.txt, ...）"""
            base_dir.mkdir(parents=True, exist_ok=True)
            version = 1
            while True:
                path = base_dir / f"{prefix}_v{version}{suffix}"
                if not path.exists():
                    return path
                version += 1
        
        # save_features の処理
        save_features_path = None
        if args.save_features and args.save_features.lower() != "none":
            if args.save_features.lower() == "auto":
                save_features_path = _get_next_versioned_path(Path("data/debug"), "features", ".txt")
            else:
                save_features_path = Path(args.save_features)
        
        # save_prompt の処理
        save_prompt_path = None
        if args.save_prompt and args.save_prompt.lower() != "none":
            if args.save_prompt.lower() == "auto":
                save_prompt_path = _get_next_versioned_path(Path("data/debug"), "prompt", ".txt")
            else:
                save_prompt_path = Path(args.save_prompt)
        if save_features_path:
            save_features_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_features_path, "w", encoding="utf-8") as f:
                f.write(features_text)
            print(f"局面特徴を保存しました: {save_features_path}", flush=True)

        if save_prompt_path:
            save_prompt_path.parent.mkdir(parents=True, exist_ok=True)
            with open(save_prompt_path, "w", encoding="utf-8") as f:
                f.write("=" * 60 + "\n")
                f.write("【システムプロンプト】\n")
                f.write("=" * 60 + "\n")
                f.write(system + "\n\n")
                f.write("=" * 60 + "\n")
                f.write("【ユーザープロンプト】\n")
                f.write("=" * 60 + "\n")
                f.write(user + "\n")
            print(f"プロンプト全文を保存しました: {save_prompt_path}", flush=True)

        cfg = OpenAIConfig(
            model=args.model,
            temperature=args.temperature,
            max_output_tokens=args.max_output_tokens,
        )

        generated, meta = call_openai(system, user, cfg)
        print("\n" + "=" * 60)
        print("【生成された解説文】")
        print("=" * 60)
        print(generated)
        print("=" * 60)
        print(f"モデル: {meta.get('model')} | response_id: {meta.get('id')}")
        return

    # ────────────────────────────────────────────────────────────────
    # バッチモード: JSONL入力→出力
    # ────────────────────────────────────────────────────────────────
    if not args.input or not args.output:
        raise ValueError("--sfen を使わない場合は --input と --output を指定してください")

    in_path = Path(args.input)
    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if out_path.exists() and not (args.resume or args.overwrite):
        raise FileExistsError(
            f"出力ファイルが既に存在します: {out_path}\n"
            "続きから生成する場合は --resume、上書きする場合は --overwrite を指定してください。"
        )

    start_index = 0
    mode = "w"
    if out_path.exists() and args.resume and not args.overwrite:
        start_index = count_valid_jsonl_lines(out_path)
        mode = "a"
        print(f"再開: 出力の有効行数 {start_index} 行を検出。続きから追記します")
    elif args.overwrite:
        mode = "w"
        print("警告: --overwrite により出力を上書きします")

    # 入力読み込み（逐次）
    cfg = OpenAIConfig(
        model=args.model,
        temperature=args.temperature,
        max_output_tokens=args.max_output_tokens,
    )

    total_lines = 0
    # まず入力の総行数だけ数える（ETA用、重いなら省略でもOK）
    with open(in_path, 'r', encoding='utf-8') as rf:
        for _ in rf:
            total_lines += 1

    if args.limit is not None:
        total_target = min(total_lines, start_index + args.limit)
    else:
        total_target = total_lines

    print(f"入力: {in_path} (総行数: {total_lines})")
    print(f"出力: {out_path} (mode={mode})")
    print(f"モデル: {cfg.model}")
    print(f"範囲: {start_index}行目から {total_target}行目まで")

    processed = 0
    success = 0
    errors = 0
    cancelled = False

    started = time.perf_counter()
    last_report = started

    def report(done_index: int) -> None:
        nonlocal last_report
        now = time.perf_counter()
        elapsed = now - started
        done = success + errors
        avg = (elapsed / done) if done > 0 else 0.0
        remaining = max(0, (total_target - done_index))
        eta = avg * remaining
        print(
            f"進捗: {done_index}/{total_target} | 完了: {success} | エラー: {errors} | 経過: {_fmt_seconds(elapsed)} | 1件平均: {avg:.2f}秒 | ETA: {_fmt_seconds(eta)}",
            flush=True,
        )
        last_report = now

    try:
        with open(in_path, 'r', encoding='utf-8') as rf, open(out_path, mode, encoding='utf-8', buffering=1) as wf:
            for idx, line in enumerate(rf):
                if idx < start_index:
                    continue
                if idx >= total_target:
                    break

                if idx == start_index or (time.perf_counter() - last_report) >= 30.0:
                    report(idx)

                processed += 1
                raw = line.strip()
                if not raw:
                    continue

                try:
                    record = json.loads(raw)
                    features_text = record.get("features_text", "")
                    if not features_text:
                        raise ValueError("features_text が空です")

                    if args.skip_if_has_commentary and record.get("commentary"):
                        continue

                    if args.skip_if_features_has_teacher_commentary and _has_teacher_commentary_in_features(features_text):
                        continue

                    features_wo = _strip_teacher_commentary(features_text)

                    rag_selected: list[RagExample] | None = None
                    if rag.enabled and rag_embeddings is not None and rag_examples is not None:
                        query_compact = _compact_features_text(features_text, max_chars=rag.max_feature_chars)
                        rag_selected = retrieve_rag_examples(
                            query_features_text=query_compact,
                            embeddings=rag_embeddings,
                            examples=rag_examples,
                            embedding_model=rag.embedding_model,
                            top_k=rag.top_k,
                            exclude_sfen=str(record.get("sfen") or "") or None,
                        )

                    system, user = make_prompt(
                        features_wo,
                        args.min_chars,
                        args.max_chars,
                        rag_examples=rag_selected,
                        use_full_features=args.rag_no_compact,
                    )

                    # リトライ（429等）
                    attempt = 0
                    while True:
                        attempt += 1
                        try:
                            generated, meta = call_openai(system, user, cfg)
                            break
                        except Exception as e:
                            if attempt >= 5:
                                raise
                            wait = min(60.0, (2 ** attempt) + random.random())
                            print(f"  APIエラー（{type(e).__name__}）: {e} → {wait:.1f}秒待って再試行({attempt}/5)", flush=True)
                            time.sleep(wait)

                    out_record = dict(record)
                    if args.sanitize_output_features_text and "features_text" in out_record:
                        out_record["features_text"] = _strip_teacher_commentary(str(out_record.get("features_text") or ""))
                    out_record["generated_commentary"] = generated
                    out_record["generation"] = {
                        "model": meta.get("model"),
                        "response_id": meta.get("id"),
                        "prompt_version": "v2_rag" if rag.enabled else "v1_no_teacher_commentary",
                        "min_chars": args.min_chars,
                        "max_chars": args.max_chars,
                    }

                    if rag.enabled:
                        out_record["rag"] = {
                            "enabled": True,
                            "top_k": rag.top_k,
                            "embedding_model": rag.embedding_model,
                            "index_base": str(rag.index_base) if rag.index_base else None,
                            "selected": [
                                {
                                    "sfen": ex.sfen,
                                    "source_file": ex.source_file,
                                }
                                for ex in (rag_selected or [])
                            ],
                        }

                    wf.write(json.dumps(out_record, ensure_ascii=False) + "\n")
                    success += 1

                    if args.sleep > 0:
                        time.sleep(args.sleep)

                except Exception as e:
                    errors += 1
                    if errors <= 5:
                        print(f"  エラー idx={idx}: {e}", flush=True)

                # 重い処理の直後にも30秒経過なら出す
                if (time.perf_counter() - last_report) >= 30.0:
                    report(idx + 1)

    except KeyboardInterrupt:
        cancelled = True
        print("\nCtrl+Cを受け取りました。ここまでに生成した分は出力ファイルに残したまま終了します...", flush=True)

    # 最終サマリ
    end = time.perf_counter()
    elapsed = end - started
    done_index = min(total_target, start_index + processed)
    done = success + errors
    avg = (elapsed / done) if done > 0 else 0.0
    print(
        f"完了: {done_index}/{total_target} | 成功: {success} | エラー: {errors} | 経過: {_fmt_seconds(elapsed)} | 1件平均: {avg:.2f}秒" + (" | 中断" if cancelled else ""),
        flush=True,
    )


if __name__ == "__main__":
    main()
