"""Shared helpers: paths, env, text normalization, evidence matching, JSON I/O."""
from __future__ import annotations

import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent


def load_env() -> None:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")


def env(name: str) -> str:
    value = os.environ.get(name, "").strip()
    if not value:
        raise RuntimeError(f"Thiếu biến môi trường {name} (xem .env.example)")
    return value


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", unicodedata.normalize("NFC", text)).strip()


def read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_json(path: Path, obj: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, default=str) + "\n", encoding="utf-8")


def chunk_hits_evidence(chunk: dict, ev: dict) -> bool:
    """Hit = same source, gold page among the pages the chunk covers, evidence fully inside."""
    pages = chunk.get("metadata", {}).get("pages") or [chunk["page"]]
    return (chunk["source_id"] == ev["source_id"] and ev["page"] in pages
            and norm(ev["evidence"]) in norm(chunk["text"]))


def groups_covered(chunks: list[dict], gold_groups: list[list[dict]]) -> list[bool]:
    """For each required evidence group: is any alternative inside any of the chunks?"""
    return [any(chunk_hits_evidence(c, ev) for c in chunks for ev in group) for group in gold_groups]
