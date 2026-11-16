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
    ap.add_argument("--allow-draft", action="store_true",
                    help="tổng hợp cả nhãn chưa xác nhận (chỉ để xem trước; ghi ra summary_draft.json)")
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
        unverified = [r["query_id"] for r in reviews if r.get("human_verified") is False]
        if unverified and not args.allow_draft:
            raise SystemExit(f"{name}: nhãn chưa được người chấm xác nhận: {unverified}. "
                             "Đọc review_sheet.md, sửa nhãn nếu cần, đặt human_verified = true "
                             "(hoặc chạy --allow-draft để xem trước, không dùng để báo cáo).")
        report = {"split": args.split, "config": name, **aggregate(cases, traces, reviews)}
        g = report["grounded_answer"]
        report["readable"] = {
            "grounded_answer_0/1/2": f"{g['0']}/{g['1']}/{g['2']} (N={g['N']}), mean={g['mean']:.2f}/2" if g["N"] else "n/a",
            "citation_validity": f"{report['citation_validity']['n']}/{report['citation_validity']['N']}",
            "abstention": f"{report['abstention']['n']}/{report['abstention']['N']}",
            "false_abstention": f"{report['false_abstention']['n']}/{report['false_abstention']['N']}",
            "tool_use": f"{report['tool_use']['n']}/{report['tool_use']['N']}"}
        report["labels"] = "chưa xác nhận" if unverified else "human-verified"
        out = d / ("summary_draft.json" if unverified else "summary_human.json")
        write_json(out, report)
        print(name, report["labels"], report["readable"], "→", out.name)


if __name__ == "__main__":
    main()
