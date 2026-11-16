"""Retrieval/context benchmark (no LLM): same corpus, index, questions and labels for every config.

Metrics on answerable questions only (unanswerable are excluded from the denominator):
- Hit@1           top-1 chunk contains a valid evidence (any required group)
- Evidence Hit@3  top-3 contains a valid evidence (any group)   ← same definition as Day 6
- Full Hit@3      top-3 covers *all* required groups (differs only for multi-hop questions)
- MRR@10          reciprocal rank of the first evidence chunk
- Context Evidence Rate: all required groups present in the packed context
  (top `context_k` chunks, deduplicated, packed under `budget_chars`; chunk that doesn't fit is skipped).

Query = original question text. Filter = the question's user-provided `filter` (Day 6 C-style), never gold.

Usage: python -m src.eval_retrieval --split dev [--configs configs/retrieval.json]
"""
from __future__ import annotations

import argparse
import statistics
import time

from .common import ROOT, groups_covered, load_env, read_json, write_json
from .retrievers import build


def pack(results: list[dict], budget: int) -> tuple[str, list[str]]:
    blocks, ids, seen = [], [], set()
    for c in results:
        if c["id"] in seen:
            continue
        seen.add(c["id"])
        block = f"[{c['id']} | trang {c['metadata']['pages']} | Chương {c['metadata'].get('chapter')}]\n{c['text']}"
        if len("\n\n".join(blocks + [block])) <= budget:
            blocks.append(block)
            ids.append(c["id"])
    return "\n\n".join(blocks), ids


def first_hit_rank(results: list[dict], q: dict) -> int | None:
    for r in results:
        if any(groups_covered([r], q["gold_groups"])):
            return r["rank"]
    return None


def run_config(cfg: dict, questions: list[dict], cache: dict) -> tuple[dict, list[dict]]:
    retriever = build(cfg["method"], cache, **cfg.get("params", {}))
    ctx_k, budget = cfg.get("context_k", 3), cfg.get("budget_chars", 4000)
    depth = max(10, ctx_k)
    traces = []
    for q in questions:
        filters = q.get("filter") if cfg.get("use_filter", True) else None
        t0 = time.perf_counter()
        results = retriever.search(q["question"], top_k=depth, filters=filters)
        ms = (time.perf_counter() - t0) * 1000
        ctx_chunks = results[:ctx_k]
        context, ctx_ids = pack(ctx_chunks, budget)
        rec = {"query_id": q["id"], "type": q["type"], "question": q["question"], "filter": filters,
               "elapsed_ms": round(ms, 1), "context_ids": ctx_ids, "context_chars": len(context),
               "results": [{"rank": r["rank"], "id": r["id"], "score": round(r["score"], 4),
                            "pages": r["metadata"]["pages"], "chapter": r["metadata"].get("chapter"),
                            **({"component_ranks": r["component_ranks"]} if "component_ranks" in r else {}),
                            "hit": any(groups_covered([r], q["gold_groups"])) if q["answerable"] else None}
                           for r in results[:max(3, ctx_k)]]}
        if q["answerable"]:
            rank = first_hit_rank(results, q)
            packed = [r for r in ctx_chunks if r["id"] in ctx_ids]
            rec.update({"hit1": bool(results) and any(groups_covered(results[:1], q["gold_groups"])),
                        "hit3": any(groups_covered(results[:3], q["gold_groups"])),
                        "full_hit3": all(groups_covered(results[:3], q["gold_groups"])),
                        "rr": 1 / rank if rank else 0.0, "first_hit_rank": rank,
                        "context_evidence": all(groups_covered(packed, q["gold_groups"]))})
        traces.append(rec)
    ans = [t for t in traces if "hit1" in t]
    n = len(ans)
    frac = lambda k: f"{sum(t[k] for t in ans)}/{n} = {sum(t[k] for t in ans) / n:.2f}"
    summary = {"config": cfg["name"], "method": cfg["method"], "info": retriever.info(),
               "context_k": ctx_k, "budget_chars": budget, "use_filter": cfg.get("use_filter", True),
               "N_answerable": n, "hit@1": frac("hit1"), "evidence_hit@3": frac("hit3"),
               "full_hit@3": frac("full_hit3"), "mrr@10": round(sum(t["rr"] for t in ans) / n, 3),
               "context_evidence_rate": frac("context_evidence"),
               "avg_context_chars": round(statistics.mean(t["context_chars"] for t in ans)),
               "median_ms": round(statistics.median(t["elapsed_ms"] for t in traces), 1),
               "cost_usd": 0,
               "misses@3": [t["query_id"] for t in ans if not t["hit3"]],
               "context_misses": [t["query_id"] for t in ans if not t["context_evidence"]]}
    return summary, traces


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", required=True, choices=("dev", "test"))
    ap.add_argument("--configs", default=str(ROOT / "configs/retrieval.json"))
    ap.add_argument("--only", nargs="*", help="chỉ chạy các config này")
    args = ap.parse_args()
    load_env()
    configs = read_json(args.configs)
    if args.only:
        configs = [c for c in configs if c["name"] in args.only]
    questions = [q for q in read_json(ROOT / "benchmark/questions.json") if q["split"] == args.split]
    cache: dict = {}
    out_dir = ROOT / "results/retrieval" / args.split
    summaries = []
    for cfg in configs:
        summary, traces = run_config(cfg, questions, cache)
        summaries.append(summary)
        write_json(out_dir / f"traces_{cfg['name']}.json", traces)
    write_json(out_dir / "summary.json", summaries)
    print(f"{'config':<22}{'Hit@1':<14}{'EvHit@3':<14}{'FullHit@3':<14}{'MRR':<7}{'CtxEv':<14}{'chars':<7}ms")
    for s in summaries:
        print(f"{s['config']:<22}{s['hit@1']:<14}{s['evidence_hit@3']:<14}{s['full_hit@3']:<14}"
              f"{s['mrr@10']:<7}{s['context_evidence_rate']:<14}{s['avg_context_chars']:<7}{s['median_ms']}")
        if s["misses@3"] or s["context_misses"]:
            print(f"    miss@3={s['misses@3']}  ctx_miss={s['context_misses']}")


if __name__ == "__main__":
    main()
