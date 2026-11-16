"""Index the advanced-challenge chunks and expose dense / BM25 / hybrid retrievers.

Dense: the same e5-small model as the main lab ("passage: " / "query: " prefixes, L2-normalised),
stored as a NumPy matrix in playground/advanced_build/ (no Day 6 DB needed for this document).
BM25 and hybrid RRF reuse src/retrievers.py unchanged.

Usage: python -m advanced.index   (builds/refreshes the embedding matrix)
"""
from __future__ import annotations

import hashlib
import json
import re
import time

import numpy as np

from src.retrievers import BM25Retriever, HybridRetriever, check_filters

from .config import BUILD

EMB_PATH = BUILD / "dense_e5_small.npy"
META_PATH = BUILD / "dense_meta.json"
MODEL = "intfloat/multilingual-e5-small"
EMBED_CHARS = 1500  # e5 limit is 512 tokens; longer figure/form texts are embedded by their head


def clean(text: str) -> str:
    text = text.replace("&nbsp;", " ")
    text = re.sub(r"_{4,}", "____", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_chunks() -> list[dict]:
    chunks = json.loads((BUILD / "chunks.json").read_text(encoding="utf-8"))
    for c in chunks:
        c["text"] = clean(c["text"])
    return chunks


def fingerprint(chunks: list[dict]) -> str:
    h = hashlib.sha256()
    for c in chunks:
        h.update(c["id"].encode() + c["text"][:EMBED_CHARS].encode())
    return h.hexdigest()[:16]


class NumpyDense:
    name = "dense"

    def __init__(self, chunks: list[dict]) -> None:
        from sentence_transformers import SentenceTransformer
        self.chunks = chunks
        self.model = SentenceTransformer(MODEL, device="cpu")
        fp = fingerprint(chunks)
        meta = json.loads(META_PATH.read_text()) if META_PATH.exists() else {}
        if EMB_PATH.exists() and meta.get("fingerprint") == fp:
            self.emb = np.load(EMB_PATH)
            self.build_seconds = meta.get("seconds")
        else:
            t0 = time.perf_counter()
            self.emb = self.model.encode(["passage: " + c["text"][:EMBED_CHARS] for c in chunks],
                                         batch_size=32, normalize_embeddings=True, convert_to_numpy=True,
                                         show_progress_bar=False).astype(np.float32)
            self.build_seconds = round(time.perf_counter() - t0, 1)
            np.save(EMB_PATH, self.emb)
            META_PATH.write_text(json.dumps({"fingerprint": fp, "model": MODEL, "n": len(chunks),
                                             "dim": int(self.emb.shape[1]), "seconds": self.build_seconds}))

    def search(self, query: str, *, top_k: int = 3, filters: dict | None = None) -> list[dict]:
        check_filters(filters)
        q = self.model.encode(["query: " + query], normalize_embeddings=True, convert_to_numpy=True)[0]
        scores = self.emb @ q
        order = np.argsort(-scores)[:top_k]
        return [{**self.chunks[i], "score": float(scores[i]), "rank": r + 1, "method": "dense"}
                for r, i in enumerate(order)]

    def info(self) -> dict:
        return {"method": "dense", "model": MODEL, "dimensions": int(self.emb.shape[1]),
                "store": "NumPy matrix (exact cosine)", "n": len(self.chunks), "embed_chars": EMBED_CHARS,
                "build_seconds": self.build_seconds}


def build(method: str, cache: dict) -> object:
    if "chunks" not in cache:
        cache["chunks"] = load_chunks()
    if method in ("dense", "hybrid") and "dense" not in cache:
        cache["dense"] = NumpyDense(cache["chunks"])
    if method in ("bm25", "hybrid") and "bm25" not in cache:
        cache["bm25"] = BM25Retriever(cache["chunks"], bigrams=True)
    if method == "hybrid":
        return HybridRetriever(cache["dense"], cache["bm25"], depth=20, rrf_k=60)
    return cache[method]


FORM_TOOL_SCHEMA = {"type": "function", "function": {
    "name": "search_form",
    "description": "Chỉ tìm trong 12 trang PHIẾU ĐIỀU TRA (phụ lục, dạng ảnh đã chép lại): câu hỏi, phương án, "
                   "mã số, hướng dẫn chuyển câu. Dùng khi câu hỏi nói về phiếu, mã câu (Q1, câu 40…) hoặc mã phương án.",
    "parameters": {"type": "object", "additionalProperties": False, "required": ["query"],
                   "properties": {"query": {"type": "string"}}}}}


def form_search_tool(cache: dict) -> dict:
    """Hybrid search restricted to questionnaire pages (kind == 'form')."""
    hy = build("hybrid", cache)

    def search(query: str, top_k: int) -> list[dict]:
        res = [r for r in hy.search(query, top_k=60) if r["metadata"]["kind"] == "form"][:top_k]
        return [{**r, "rank": i + 1} for i, r in enumerate(res)]
    return {"search_form": {"schema": FORM_TOOL_SCHEMA, "search": search}}


def header(c: dict) -> str:
    m = c["metadata"]
    kind = {"text": "văn bản", "table": "bảng", "figure": "hình/biểu đồ", "form": "phiếu điều tra (ảnh)"}[m["kind"]]
    cap = f" · {m['caption'][:90]}" if m.get("caption") else ""
    return f"trang in {m['printed_page']} / PDF {m['pdf_page']} · {kind}{cap}"


if __name__ == "__main__":
    t = time.perf_counter()
    d = NumpyDense(load_chunks())
    print(d.info(), f"{time.perf_counter() - t:.1f}s")
