"""Build the Day 7 corpus + benchmark from Day 6 outputs.

- Corpus: Day 6 strategy-B chunks (one Điều per chunk, same rows as the pgvector index).
- Benchmark: Day 6 questions (q01–q20) + Day 7 additions (benchmark/extra_questions.json).
  Each evidence gets its page resolved from the Day 6 normalized page text, and must lie
  entirely inside one chunk of the stated article on that page (otherwise: hard error).

Usage: python -m src.prepare_data [--day6 ../K5-L3-Day06-DataIngestionEngineering]
"""
from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from .common import ROOT, norm, write_json


def load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def convert_chunk(c: dict) -> dict:
    m = c["metadata"]
    return {"id": c["chunk_id"], "text": c["text"], "source_id": c["document_id"],
            "source": "Bộ luật Lao động 2019 (45/2019/QH14)", "page": c["page"],
            "metadata": {"pages": m["pages"], "chapter": m.get("chapter"),
                         "chapter_title": m.get("chapter_title"), "section": m.get("section"),
                         "articles": m.get("articles") or [], "article_title": m.get("article_title"),
                         "part": m.get("part"), "parts": m.get("parts"),
                         "content_hash": m.get("content_hash"), "file": c["source"]}}


def resolve(ev: dict, pages: list[dict], chunks: list[dict], qid: str, source_id: str) -> dict:
    text = norm(ev["evidence"])
    found = [p["page"] for p in pages if text in norm(p["text"])]
    if ev.get("page") is not None and ev["page"] not in found:
        raise ValueError(f"{qid}: evidence không nằm trên trang {ev['page']} (tìm thấy: {found})")
    page = ev.get("page") or (found[0] if len(found) == 1 else None)
    if page is None:
        raise ValueError(f"{qid}: không xác định được trang duy nhất cho evidence (tìm thấy: {found})")
    holders = [c["id"] for c in chunks if ev["article"] in c["metadata"]["articles"]
               and page in c["metadata"]["pages"] and text in norm(c["text"])]
    if not holders:
        raise ValueError(f"{qid}: evidence không nằm trọn trong chunk nào của Điều {ev['article']}")
    return {"source_id": source_id, "page": page, "article": ev["article"], "evidence": ev["evidence"],
            "chunk_ids_for_audit": holders}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--day6", type=Path, default=ROOT.parent / "K5-L3-Day06-DataIngestionEngineering")
    args = ap.parse_args()
    day6 = args.day6.resolve()
    raw_chunks = load_jsonl(day6 / "starter/results/chunks_B.jsonl")
    pages = load_jsonl(day6 / "starter/results/pages.jsonl")
    chunks = [convert_chunk(c) for c in raw_chunks]
    if len({c["id"] for c in chunks}) != len(chunks):
        raise ValueError("chunk ID trùng")
    source_id = chunks[0]["source_id"]

    questions = []
    for q in load_jsonl(day6 / "benchmark/questions.jsonl"):
        questions.append({"id": q["id"], "split": q["split"], "type": q["type"], "origin": "day6",
                          "question": q["question"], "answerable": True,
                          "expected_answer": q["expected_answer"], "filter": q.get("filter"),
                          "gold_groups": [[{"article": q["gold_article"], "page": q["gold_page"],
                                            "evidence": q["evidence_quote"]}]]})
    for q in json.loads((ROOT / "benchmark/extra_questions.json").read_text(encoding="utf-8")):
        questions.append({**q, "origin": "day7", "answerable": q.get("answerable", True)})

    for q in questions:
        if q["answerable"]:
            q["gold_groups"] = [[resolve(ev, pages, chunks, q["id"], source_id) for ev in group]
                                for group in q["gold_groups"]]
            # Flat list (alternatives) kept for compatibility with starter/baseline.py
            q["gold"] = [{k: ev[k] for k in ("source_id", "page", "evidence")}
                         for group in q["gold_groups"] for ev in group]
    if len({q["id"] for q in questions}) != len(questions):
        raise ValueError("question ID trùng")

    write_json(ROOT / "data/day7/chunks.json", chunks)
    write_json(ROOT / "benchmark/questions.json", questions)
    write_json(ROOT / "benchmark/cases.json",
               [{"id": q["id"], "split": q["split"], "answerable": q["answerable"]} for q in questions])
    stats = Counter((q["split"], "answerable" if q["answerable"] else "unanswerable") for q in questions)
    print(f"chunks: {len(chunks)}  pages: {len(pages)}")
    print("questions:", dict(sorted(stats.items())))
    print("multi_hop:", sum(len(q.get("gold_groups", [])) > 1 for q in questions))


if __name__ == "__main__":
    main()
