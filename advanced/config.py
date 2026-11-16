"""Advanced challenge: source document, paths and model settings.

The PDF and everything derived from it (page text, chunks, figure crops, Gemini descriptions)
live under pdf_docs/ (gitignored): the publisher's reuse terms were not confirmed, so the repo
ships only the link, the checksum and the scripts that rebuild everything.
"""
from __future__ import annotations

import os

from src.common import ROOT

DOC_ID = "bdds2025"
DOC_TITLE = ("Kết quả chủ yếu Điều tra biến động dân số và kế hoạch hóa gia đình "
             "thời điểm 01/4/2025 (Cục Thống kê, Bộ Tài chính)")
SOURCE_URL = ("https://www.nso.gov.vn/wp-content/uploads/2026/08/"
              "Sach-ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-2025.-pdf.pdf")
LANDING_URL = ("https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/08/"
               "ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-va-ke-hoach-hoa-gia-dinh-thoi-diem-01-4-2025/")
SHA256 = "d2178d7b8fb71699c67eed4c4382d10c8658ea0bca06793ae4d2abeee706c2fe"
PAGES = 237
PRINTED_OFFSET = 1  # printed page number = PDF page - 1

SRC_DIR = ROOT / "pdf_docs"
PDF_PATH = SRC_DIR / "ket-qua-dieu-tra-bien-dong-dan-so-2025.pdf"
BUILD = SRC_DIR / "build"
FIG_DIR = BUILD / "figures"
CACHE_DIR = BUILD / "gemini_cache"

GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.5-flash")
# USD per 1M tokens (Google AI Studio pricing page, gemini-3.6-flash promo rate through 2026-12-31;
# gemini-3.5-flash requests are routed to 3.6-flash). Output includes thinking tokens.
GEMINI_PRICE = (0.75, 3.75)
