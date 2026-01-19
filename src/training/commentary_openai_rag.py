# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
import json
import time
from pathlib import Path

from .commentary_openai_helpers import (
    compact_features_text,
    count_valid_jsonl_lines,
    fmt_seconds,
    strip_teacher_commentary,
    truncate_text,
)
from .openai_client import get_openai_client


def embed_texts(texts: list[str], embedding_model: str) -> list[list[float]]:
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


def rag_paths(index_base: Path) -> tuple[Path, Path, Path]:
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

    npz_path, meta_path, info_path = rag_paths(index_base)
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
        vectors = embed_texts(batch_texts, embedding_model=embedding_model)
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
                    f"{fmt_seconds(elapsed)} 経過 | 残り { fmt_seconds(eta) }",
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
            features_text_full = strip_teacher_commentary(features_text)
            # 埋め込み用に短縮
            compact = compact_features_text(features_text, max_chars=max_feature_chars)
            if not compact:
                continue

            batch_texts.append(compact)
            batch_meta.append(
                {
                    "sfen": rec.get("sfen", ""),
                    "features_text": compact,
                    "features_text_full": features_text_full,
                    "commentary": truncate_text(str(commentary), max_example_commentary_chars),
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

    npz_path, meta_path, _info_path = rag_paths(index_base)
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

    vec = embed_texts([query_features_text], embedding_model=embedding_model)[0]
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
