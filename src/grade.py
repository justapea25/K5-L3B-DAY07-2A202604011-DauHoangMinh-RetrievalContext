"""Aggregate human labels (reviews.json) with traces using the provided starter/agent_metrics.py.

Fill results/agent/<split>/<config>/reviews.json first:
  answerable:   answer_grade 0/1/2 (abstain → 0), citation_support [true/false per citation]
  unanswerable: abstention_correct true/false, citation_support [] (or one bool per citation)
Labels are human judgments after reading the cited chunk text; do not derive them from IDs.

Usage: python -m src.grade --split dev --config agent_dense_single [agent_hybrid_multi ...]
"""
from __future__ import annotations

import argparse
import sys

from .common import ROOT, read_json, write_json

sys.path.insert(0, str(ROOT / "starter"))
from agent_metrics import aggregate  # noqa: E402


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", required=True, choices=("dev", "test"))
    ap.add_argument("--config", nargs="+", required=True)
    args = ap.parse_args()
    cases = [c for c in read_json(ROOT / "benchmark/cases.json") if c["split"] == args.split]
    for name in args.config:
        d = ROOT / "results/agent" / args.split / name
        traces = read_json(d / "traces.json")
        reviews = read_json(d / "reviews.json")
        missing = [r["query_id"] for r in reviews if r.get("status") != "error" and (
            (r["answerable"] and r.get("answer_grade") is None) or
            (not r["answerable"] and r.get("abstention_correct") is None) or
            any(v is None for v in r.get("citation_support", [])))]
        if missing:
            raise SystemExit(f"{name}: còn thiếu nhãn cho {missing}")
        report = {"split": args.split, "config": name, **aggregate(cases, traces, reviews)}
        g = report["grounded_answer"]
        report["readable"] = {
            "grounded_answer_0/1/2": f"{g['0']}/{g['1']}/{g['2']} (N={g['N']}), mean={g['mean']:.2f}/2" if g["N"] else "n/a",
            "citation_validity": f"{report['citation_validity']['n']}/{report['citation_validity']['N']}",
            "abstention": f"{report['abstention']['n']}/{report['abstention']['N']}",
            "false_abstention": f"{report['false_abstention']['n']}/{report['false_abstention']['N']}",
            "tool_use": f"{report['tool_use']['n']}/{report['tool_use']['N']}"}
        write_json(d / "summary_human.json", report)
        print(name, report["readable"])


if __name__ == "__main__":
    main()
