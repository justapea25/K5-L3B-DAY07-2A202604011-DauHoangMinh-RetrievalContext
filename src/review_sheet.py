"""Write a Markdown review sheet per config so a human can grade answers against the cited text.

For each question: question, expected answer / absence reason, gold evidence, agent answer,
each citation with the full cited chunk text, searches made, and automatic checks (proxies).
Grade in reviews.json next to it, then run src.grade.

Usage: python -m src.review_sheet --split test --config agent_dense_single agent_hybrid_multi_budget_alias
"""
from __future__ import annotations

import argparse

from .common import ROOT, chunk_hits_evidence, groups_covered, read_json


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--split", required=True, choices=("dev", "test"))
    ap.add_argument("--config", nargs="+", required=True)
    args = ap.parse_args()
    qs = {q["id"]: q for q in read_json(ROOT / "benchmark/questions.json")}
    chunks = {c["id"]: c for c in read_json(ROOT / "data/day7/chunks.json")}
    for name in args.config:
        d = ROOT / "results/agent" / args.split / name
        lines = [f"# Phiếu chấm — {name} ({args.split})", "",
                 "Chấm trong `reviews.json`: `answer_grade` 0 = sai/thiếu evidence, 1 = đúng một phần, "
                 "2 = đúng và đủ (từ chối câu có đáp án = 0); `citation_support` = true nếu đoạn được trích "
                 "thực sự hỗ trợ ý đã trả lời; câu thiếu evidence: `abstention_correct`.", ""]
        for t in read_json(d / "traces.json"):
            q = qs[t["query_id"]]
            lines += [f"## {q['id']} · {q['type']} · status = `{t['status']}`", "",
                      f"**Câu hỏi:** {q['question']}", ""]
            if q["answerable"]:
                lines.append(f"**Đáp án chuẩn:** {q['expected_answer']}")
                for i, g in enumerate(q["gold_groups"], 1):
                    for ev in g:
                        lines.append(f"- Evidence {i} (Điều {ev['article']}, trang {ev['page']}): “{ev['evidence']}”")
            else:
                lines.append(f"**Kỳ vọng:** từ chối. Lý do thiếu: {q['absence_reason']}")
            lines += ["", f"**Agent trả lời:** {t.get('answer')}"]
            if t.get("abstain_reason"):
                lines.append(f"*(lý do từ chối: {t['abstain_reason']})*")
            if t.get("error"):
                lines.append(f"**LỖI:** {t['error']}")
            lines.append("")
            lines.append("**Tìm kiếm:** " + "; ".join(f"`{e['query']}`" for e in t["events"] if e["event"] == "search"))
            ctx = [chunks[i] for i in t.get("final_context_ids", [])]
            if q["answerable"]:
                cov = groups_covered(ctx, q["gold_groups"])
                lines.append(f"**Auto:** context chứa evidence {sum(cov)}/{len(cov)} nhóm; "
                             f"{t['n_searches']} lượt tìm; {t.get('elapsed_s')} s; ${t.get('cost_usd')}")
            for k, cid in enumerate(t["citations"], 1):
                c = chunks[cid]
                gold_hit = q["answerable"] and any(chunk_hits_evidence(c, ev) for g in q["gold_groups"] for ev in g)
                lines += ["", f"<details><summary>Citation {k}: {cid} (trang {c['metadata']['pages']})"
                              f"{' — chứa evidence chuẩn' if gold_hit else ''}</summary>", "",
                          "```text", c["text"], "```", "</details>"]
            lines += ["", "---", ""]
        (d / "review_sheet.md").write_text("\n".join(lines), encoding="utf-8")
        print("wrote", d / "review_sheet.md")


if __name__ == "__main__":
    main()
