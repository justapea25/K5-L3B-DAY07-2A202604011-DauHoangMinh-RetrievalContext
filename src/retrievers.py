"""Three retrieval methods over the same corpus (Day 6 strategy-B chunks).

1. DenseRetriever  – e5-small query embedding → Day 6 pgvector table (exact cosine, strategy 'B').
2. BM25Retriever   – Okapi BM25 in pure Python; tokenization = syllables, optionally + bigrams
                     (Vietnamese words are mostly 1–2 syllables, so bigrams approximate words).
3. HybridRetriever – Reciprocal Rank Fusion of dense + BM25 rankings (rank-based, so the two
                     incomparable score scales never get added together).

Every result: id, text, source_id, source, page, metadata, score, rank, method.
Filters: only {'chapter': <roman numeral>} is supported, taken from the question's
user-provided `filter` field or from the agent tool argument — never from gold.
"""
from __future__ import annotations

import math
import re
import time
import unicodedata
from collections import Counter
from typing import Any

from .common import ROOT, env, read_json

ALLOWED_FILTERS = {"chapter"}


def check_filters(filters: dict[str, Any] | None) -> dict[str, Any]:
    filters = {k: v for k, v in (filters or {}).items() if v not in (None, "")}
    bad = set(filters) - ALLOWED_FILTERS
    if bad:
        raise ValueError(f"filter không hỗ trợ: {sorted(bad)}")
    return filters


def load_chunks() -> list[dict]:
    return read_json(ROOT / "data/day7/chunks.json")


def _result(chunk: dict, score: float, rank: int, method: str, **extra) -> dict:
    return {**chunk, "score": float(score), "rank": rank, "method": method, **extra}


# ---------------------------------------------------------------- dense
class DenseRetriever:
    name = "dense"
    STRATEGY = "B"  # Day 6 rows used as the corpus
    MODEL = "intfloat/multilingual-e5-small"

    def __init__(self, chunks: list[dict] | None = None) -> None:
        import psycopg
        from pgvector.psycopg import register_vector
        from sentence_transformers import SentenceTransformer

        self.by_id = {c["id"]: c for c in (chunks or load_chunks())}
        self.model = SentenceTransformer(self.MODEL, device="cpu")
        self.dimensions = self.model.get_sentence_embedding_dimension()
        self.conn = psycopg.connect(env("DATABASE_URL"), connect_timeout=5, autocommit=True)
        register_vector(self.conn)
        n, model, dim = self.conn.execute(
            "SELECT count(*), min(embedding_model), min(vector_dims(embedding)) FROM chunks "
            "WHERE strategy = %s", (self.STRATEGY,)).fetchone()
        if n != len(self.by_id):
            raise RuntimeError(f"pgvector có {n} dòng strategy B, corpus có {len(self.by_id)} chunk")
        if model != self.MODEL or dim != self.dimensions:
            raise RuntimeError(f"index dùng {model}/{dim}d, query model {self.MODEL}/{self.dimensions}d")

    def embed(self, query: str):
        return self.model.encode(["query: " + query], normalize_embeddings=True,
                                 convert_to_numpy=True)[0]

    def search(self, query: str, *, top_k: int = 3, filters: dict | None = None) -> list[dict]:
        filters = check_filters(filters)
        sql = ("SELECT chunk_id, 1 - (embedding <=> %s) AS score FROM chunks WHERE strategy = %s"
               + (" AND chapter = %s" if "chapter" in filters else "")
               + " ORDER BY embedding <=> %s LIMIT %s")
        q = self.embed(query)
        params = [q, self.STRATEGY] + ([filters["chapter"]] if "chapter" in filters else []) + [q, top_k]
        rows = self.conn.execute(sql, params).fetchall()
        return [_result(self.by_id[cid], s, i + 1, self.name) for i, (cid, s) in enumerate(rows)]

    def info(self) -> dict:
        return {"method": "dense", "model": self.MODEL, "dimensions": self.dimensions,
                "store": "PostgreSQL 16 + pgvector 0.8.7 (Day 6), table chunks, strategy B",
                "metric": "cosine (exact scan)", "query_prefix": "query: "}


# ---------------------------------------------------------------- BM25
def tokenize(text: str, bigrams: bool = True) -> list[str]:
    toks = re.findall(r"\w+", unicodedata.normalize("NFC", text).casefold())
    if bigrams:
        toks = toks + [f"{a}_{b}" for a, b in zip(toks, toks[1:])]
    return toks


class BM25Retriever:
    name = "bm25"

    def __init__(self, chunks: list[dict] | None = None, *, k1: float = 1.5, b: float = 0.75,
                 bigrams: bool = True) -> None:
        self.chunks = chunks or load_chunks()
        self.k1, self.b, self.bigrams = k1, b, bigrams
        t0 = time.perf_counter()
        self.tfs = [Counter(tokenize(c["text"], bigrams)) for c in self.chunks]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avgdl = sum(self.lens) / len(self.lens)
        df = Counter(t for tf in self.tfs for t in tf)
        n = len(self.chunks)
        self.idf = {t: math.log(1 + (n - d + 0.5) / (d + 0.5)) for t, d in df.items()}
        self.index_seconds = time.perf_counter() - t0

    def search(self, query: str, *, top_k: int = 3, filters: dict | None = None) -> list[dict]:
        filters = check_filters(filters)
        q_terms = [t for t in set(tokenize(query, self.bigrams)) if t in self.idf]
        scored = []
        for c, tf, dl in zip(self.chunks, self.tfs, self.lens):
            if "chapter" in filters and c["metadata"].get("chapter") != filters["chapter"]:
                continue
            s = 0.0
            for t in q_terms:
                f = tf.get(t)
                if f:
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avgdl))
            if s > 0:
                scored.append((s, c))
        scored.sort(key=lambda x: (-x[0], x[1]["id"]))
        return [_result(c, s, i + 1, self.name) for i, (s, c) in enumerate(scored[:top_k])]

    def info(self) -> dict:
        return {"method": "bm25", "k1": self.k1, "b": self.b,
                "tokenizer": "syllable unigram" + (" + bigram" if self.bigrams else ""),
                "index_seconds": round(self.index_seconds, 3)}


# ---------------------------------------------------------------- hybrid (RRF)
class HybridRetriever:
    name = "hybrid"

    def __init__(self, dense: DenseRetriever, bm25: BM25Retriever, *, depth: int = 20,
                 rrf_k: int = 60, weights: tuple[float, float] = (1.0, 1.0)) -> None:
        self.dense, self.bm25 = dense, bm25
        self.depth, self.rrf_k, self.weights = depth, rrf_k, weights

    def search(self, query: str, *, top_k: int = 3, filters: dict | None = None) -> list[dict]:
        lists = [self.dense.search(query, top_k=self.depth, filters=filters),
                 self.bm25.search(query, top_k=self.depth, filters=filters)]
        fused: dict[str, dict] = {}
        for w, results in zip(self.weights, lists):
            for r in results:
                entry = fused.setdefault(r["id"], {"chunk": r, "score": 0.0, "ranks": {}})
                entry["score"] += w / (self.rrf_k + r["rank"])
                entry["ranks"][r["method"]] = r["rank"]
        order = sorted(fused.values(), key=lambda e: (-e["score"], e["chunk"]["id"]))[:top_k]
        out = []
        for i, e in enumerate(order):
            base = {k: v for k, v in e["chunk"].items() if k not in ("score", "rank", "method")}
            out.append(_result(base, e["score"], i + 1, self.name, component_ranks=e["ranks"]))
        return out

    def info(self) -> dict:
        return {"method": "hybrid_rrf", "depth": self.depth, "rrf_k": self.rrf_k,
                "weights": {"dense": self.weights[0], "bm25": self.weights[1]},
                "components": [self.dense.info(), self.bm25.info()]}


def build(method: str, cache: dict | None = None, **kw) -> Any:
    """Factory with a cache so the embedding model / DB connection load once."""
    cache = cache if cache is not None else {}
    if "dense" not in cache and method in ("dense", "hybrid"):
        cache["dense"] = DenseRetriever()
    if method == "dense":
        return cache["dense"]
    bigrams = kw.get("bigrams", True)
    key = f"bm25:{bigrams}"
    if key not in cache:
        cache[key] = BM25Retriever(bigrams=bigrams)
    if method == "bm25":
        return cache[key]
    if method == "hybrid":
        return HybridRetriever(cache["dense"], cache[key], depth=kw.get("depth", 20),
                               rrf_k=kw.get("rrf_k", 60))
    raise ValueError(f"method không hợp lệ: {method}")
