"""Run the real agent on one split for one or more configs; save full traces + automatic metrics.

Automatic metrics are *proxies* computed against gold AFTER the run (gold never enters the agent):
  tool_use, status counts, abstention on unanswerable, false abstention on answerable,
  agent Context Evidence Rate (final context covers all required evidence groups),
  citation_gold_hit (share of citations whose chunk contains a gold evidence).
Answer correctness and citation support are graded by a human in reviews_<config>.json
(see src/grade.py); on the test split a draft file with empty labels is written next to the traces.

Usage: python -m src.run_agent --split dev [--only agent_dense_k3] [--ids q01 q02]
"""
from __future__ import annotations

import argparse
import statistics
import time

from .agent import Agent
from .common import ROOT, chunk_hits_evidence, groups_covered, load_env, read_json, write_json
from .retrievers import build


def proxies(traces: list[dict], qs: dict[str, dict]) -> dict:
    ok = [t for t in traces if t["status"] != "error"]
    ans = [t for t in ok if qs[t["query_id"]]["answerable"]]
    una = [t for t in ok if not qs[t["query_id"]]["answerable"]]
    cites = [(t, c) for t in ans for c in t["citations"]]
    gold_cite = sum(any(chunk_hits_evidence(t["_ctx"][c], ev) for g in qs[t["query_id"]]["gold_groups"] for ev in g)
                    for t, c in cites if c in t["_ctx"])
    ctx_ev = sum(all(groups_covered(list(t["_ctx"].values()), qs[t["query_id"]]["gold_groups"])) for t in ans)
    f = lambda n, d: f"{n}/{d}" + (f" = {n / d:.2f}" if d else " (không áp dụng)")
    searches = [t["n_searches"] for t in ok]
    return {"runs": len(traces), "errors": len(traces) - len(ok),
            "tool_use": f(sum(t["n_searches"] > 0 for t in ok), len(ok)),
            "searches_distribution": {str(k): searches.count(k) for k in sorted(set(searches))},
            "answered_on_answerable": f(sum(t["status"] == "answered" for t in ans), len(ans)),
            "false_abstention": f(sum(t["status"] == "abstain" for t in ans), len(ans)),
            "abstention_on_unanswerable": f(sum(t["status"] == "abstain" for t in una), len(una)),
            "agent_context_evidence_rate": f(ctx_ev, len(ans)),
            "citation_gold_hit_proxy": f(gold_cite, len(cites)),
            "mean_searches": round(statistics.mean(searches), 2) if searches else None,
            "median_latency_s": round(statistics.median(t["elapsed_s"] for t in ok), 2) if ok else None,
            "total_tokens_in": sum(t.get("tokens_in", 0) for t in ok),
            "total_tokens_out": sum(t.get("tokens_out", 0) for t in ok),
            "total_cost_usd": round(sum(t.get("cost_usd", 0) for t in ok), 5)}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", required=True, choices=("dev", "test"))
    ap.add_argument("--configs", default=str(ROOT / "configs/agent.json"))
    ap.add_argument("--only", nargs="*")
    ap.add_argument("--ids", nargs="*", help="chỉ chạy các câu này (debug)")
    args = ap.parse_args()
    load_env()
    configs = read_json(args.configs)
    if args.only:
        configs = [c for c in configs if c["name"] in args.only]
    questions = [q for q in read_json(ROOT / "benchmark/questions.json") if q["split"] == args.split]
    if args.ids:
        questions = [q for q in questions if q["id"] in args.ids]
    qs = {q["id"]: q for q in questions}
    cache: dict = {}
    for cfg in configs:
        retriever = build(cfg["method"], cache, **cfg.get("retriever_params", {}))
        agent = Agent(retriever, **cfg.get("agent", {}))
        traces = []
        for q in questions:
            # Only the question text and its user-provided filter go to the agent.
            try:
                out = agent.run(q["question"], filters=q.get("filter"))
            except Exception as e:  # provider / store error: record, never replace with fake output
                out = {"status": "error", "error": f"{type(e).__name__}: {e}", "answer": None,
                       "citations": [], "events": [], "n_searches": 0, "elapsed_s": None}
            ctx = {i: cache_chunk(i) for i in out.get("final_context_ids", [])}
            traces.append({"query_id": q["id"], "split": q["split"], "config": cfg["name"],
                           "question": q["question"], "filter": q.get("filter"), **out, "_ctx": ctx})
            print(f"[{cfg['name']}] {q['id']}: {out['status']:<9} searches={out['n_searches']} "
                  f"cites={out['citations']} {out.get('elapsed_s')}s")
            time.sleep(0.2)
        summary = {"config": cfg, "split": args.split, "model": agent.model,
                   "retriever": retriever.info(), **proxies(traces, qs)}
        out_dir = ROOT / "results/agent" / args.split / cfg["name"]
        write_json(out_dir / "traces.json", [{k: v for k, v in t.items() if k != "_ctx"} for t in traces])
        write_json(out_dir / "summary_auto.json", summary)
        draft = out_dir / "reviews.json"
        if args.split == "test" and not draft.exists():  # only test is human-graded
            write_json(draft, [{"query_id": t["query_id"], "answerable": qs[t["query_id"]]["answerable"],
                                "status": t["status"], "answer_grade": None,
                                "citation_support": [None] * len(t["citations"]),
                                "abstention_correct": None, "note": ""} for t in traces])
        print({k: v for k, v in summary.items() if k not in ("config", "retriever")})


_CHUNKS: dict | None = None


def cache_chunk(cid: str) -> dict:
    global _CHUNKS
    if _CHUNKS is None:
        _CHUNKS = {c["id"]: c for c in read_json(ROOT / "data/day7/chunks.json")}
    return _CHUNKS[cid]


if __name__ == "__main__":
    main()
