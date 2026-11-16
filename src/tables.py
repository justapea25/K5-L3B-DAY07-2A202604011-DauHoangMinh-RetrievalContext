"""Print Markdown comparison tables from saved summaries (retrieval + agent auto + human labels).

Usage: python -m src.tables --split dev
"""
from __future__ import annotations

import argparse

from .common import ROOT, read_json


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", required=True, choices=("dev", "test"))
    args = ap.parse_args()
    rp = ROOT / "results/retrieval" / args.split / "summary.json"
    if rp.exists():
        print(f"### Retrieval ({args.split}, query gốc, filter người dùng)\n")
        print("| Config | Hit@1 | Evidence Hit@3 | Full Hit@3 | MRR@10 | Context Evidence | Context (ký tự TB) | ms (trung vị) |")
        print("|---|---|---|---|---|---|---|---|")
        for s in read_json(rp):
            print(f"| {s['config']} | {s['hit@1']} | {s['evidence_hit@3']} | {s['full_hit@3']} | {s['mrr@10']} | "
                  f"{s['context_evidence_rate']} | {s['avg_context_chars']} | {s['median_ms']} |")
        print()
    ad = ROOT / "results/agent" / args.split
    if ad.exists():
        print(f"### Agent ({args.split}, chỉ số tự động — proxy)\n")
        print("| Config | Trả lời câu có đáp án | Từ chối sai | Từ chối đúng (thiếu evidence) | Context Evidence | Citation chứa gold | Lượt tìm TB | Latency (s, trung vị) | Token in/out | Chi phí USD |")
        print("|---|---|---|---|---|---|---|---|---|---|")
        for d in sorted(p for p in ad.iterdir() if (p / "summary_auto.json").exists()):
            s = read_json(d / "summary_auto.json")
            print(f"| {d.name} | {s['answered_on_answerable']} | {s['false_abstention']} | {s['abstention_on_unanswerable']} | "
                  f"{s['agent_context_evidence_rate']} | {s['citation_gold_hit_proxy']} | {s['mean_searches']} | "
                  f"{s['median_latency_s']} | {s['total_tokens_in']}/{s['total_tokens_out']} | {s['total_cost_usd']} |")
        human = [d for d in sorted(ad.iterdir()) if (d / "summary_human.json").exists()]
        if human:
            print(f"\n### Agent ({args.split}, nhãn chấm tay)\n")
            print("| Config | Grounded 0/1/2 | Trung bình /2 | Citation hợp lệ | Abstention | Từ chối sai | Tool use | Lỗi |")
            print("|---|---|---|---|---|---|---|---|")
            for d in human:
                h = read_json(d / "summary_human.json")
                g = h["grounded_answer"]
                cv = h["citation_validity"]
                print(f"| {d.name} | {g['0']}/{g['1']}/{g['2']} | {g['mean']:.2f} | {cv['n']}/{cv['N']} | "
                      f"{h['abstention']['n']}/{h['abstention']['N']} | {h['false_abstention']['n']}/{h['false_abstention']['N']} | "
                      f"{h['tool_use']['n']}/{h['tool_use']['N']} | {h['provider_errors']} |")


if __name__ == "__main__":
    main()
