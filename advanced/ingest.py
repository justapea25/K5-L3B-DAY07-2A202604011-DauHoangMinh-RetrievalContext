"""Ingest the 237-page report into retrievable chunks (text, tables, figures, questionnaire pages).

- Text and tables: PyMuPDF words → lines rebuilt from coordinates; a horizontal gap > GAP pt
  becomes a " | " cell separator, so table rows keep their row/column alignment.
  Captions ("Hình x.y:", "Biểu x.y:", "Biểu N") start new units; multi-page "Biểu N (Tiếp theo)"
  carry the table's full title. Long units are split; table chunks repeat their header.
- Figures ("Hình x.y"): the graphic's bbox = union of image/drawing rects under the caption;
  the crop (caption + graphic) is rendered at 150 dpi and described by Gemini (vision).
  The chunk = caption + Gemini description + any text labels inside the bbox.
- Questionnaire pages (scanned-like full-page images, Phụ lục 1): transcribed by Gemini.
Every chunk keeps pdf_page, printed page, kind, caption and (for figures) bbox + crop path.

Usage: python -m advanced.ingest [--no-gemini]
"""
from __future__ import annotations

import argparse
import json
import re
import time

import pymupdf

from src.common import load_env, write_json

from .config import BUILD, DOC_ID, FIG_DIR, PDF_PATH, PRINTED_OFFSET

GAP = 6.0          # pt; horizontal gap that separates table cells
MAX_CHARS = 1400   # chunk size (e5 limit is 512 tokens)
SKIP_PAGES = {1, 2, 236, 237}  # covers / imprint
FIG_RE = re.compile(r"^Hình\s*(\d+\.\d+)\s*:")
TAB_RE = re.compile(r"^Biểu\s*(\d+(?:\.\d+)?)\s*(\(Tiếp theo\))?\s*:?")
HEAD_RE = re.compile(r"^(PHẦN [IVX]+\b.*|CHƯƠNG \d+.*|\d{1,2}(\.\d{1,2})+\.\s+\S.*|\d{1,2}\.\s+[A-ZĐÂĂÊÔƠƯ].*"
                     r"|Phụ lục \d+.*)$")
UPPER_RE = re.compile(r"^[^a-zàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]{12,}$")

FIG_PROMPT = """Đây là ảnh cắt từ một hình trong báo cáo thống kê "{title}" (trang {printed}): {caption}.
Mô tả CHÍNH XÁC nội dung bằng tiếng Việt để phục vụ tra cứu:
1) Loại biểu đồ/hình, tiêu đề, đơn vị, các trục, chú giải (từng chuỗi số liệu).
2) Liệt kê MỌI nhãn số liệu hiển thị trên hình, mỗi dòng dạng "<danh mục> – <chuỗi>: <giá trị>". Chỉ ghi số nhìn thấy trên hình; nếu không có nhãn và phải đọc theo trục thì ghi "(ước lượng theo trục)".
3) 2–4 nhận xét so sánh hoặc xu hướng chắc chắn nhìn thấy được trên hình.
Không suy diễn ngoài hình, không thêm số liệu không có trên hình."""

FORM_PROMPT = """Đây là một trang trong Phiếu điều tra (phụ lục) của báo cáo "{title}", trang {printed}.
Chép lại chính xác bằng tiếng Việt, dạng văn bản thuần (không dùng bảng markdown, không dùng HTML):
- Tên phần/mục và các bước kiểm tra (KT…) như trên trang.
- Mỗi câu hỏi ghi MỘT lần (dù phiếu lặp lại cùng câu cho nhiều cột "người thứ 01, 02…"): "Câu <mã>. <nội dung câu hỏi>".
- Mỗi phương án trả lời một dòng: "  - <PHƯƠNG ÁN> = <mã số>". Nếu có mũi tên/ký hiệu chuyển câu ĐI RA TỪ phương án đó, ghi ngay trên cùng dòng: "→ <đích>" (ví dụ "→ C35", "→ KẾT THÚC PHỎNG VẤN"). Mũi tên thuộc về phương án mà nó xuất phát; xem kỹ hướng mũi tên trên ảnh.
- Ghi chú hướng dẫn trong ngoặc như trên trang.
Không thêm thông tin không có trên trang, không giải thích."""


def page_lines(page) -> list[dict]:
    """Rebuild visual lines from word boxes; cells separated by ' | '."""
    words = sorted(page.get_text("words"), key=lambda w: ((w[1] + w[3]) / 2, w[0]))
    rows: list[list] = []
    for w in words:
        yc = (w[1] + w[3]) / 2
        if rows and abs(rows[-1][0] - yc) <= 2.5:
            rows[-1][1].append(w)
        else:
            rows.append([yc, [w]])
    out = []
    for yc, ws in rows:
        ws.sort(key=lambda w: w[0])
        text, prev = "", None
        for w in ws:
            if prev is not None:
                text += " | " if w[0] - prev[2] > GAP else " "
            text += w[4]
            prev = w
        out.append({"y0": min(w[1] for w in ws), "y1": max(w[3] for w in ws), "text": text.strip()})
    # drop the printed page number line at the top/bottom
    return [ln for ln in out if not re.fullmatch(r"\d{1,3}", ln["text"])]


def is_numeric_row(text: str) -> bool:
    cells = [c.strip() for c in text.split("|")]
    return sum(bool(re.fullmatch(r"[-–]?[\d.,]+%?|-|–", c)) for c in cells) >= 2


def figure_bbox(page, cap_y1: float, next_y: float) -> pymupdf.Rect:
    rects = [pymupdf.Rect(i["bbox"]) for i in page.get_image_info()]
    rects += [pymupdf.Rect(d["rect"]) for d in page.get_drawings()]
    inside = [r for r in rects if r.y0 >= cap_y1 - 2 and r.y1 <= next_y + 2 and r.height > 1 and r.width > 1]
    if inside:
        bb = pymupdf.Rect(inside[0])
        for r in inside[1:]:
            bb |= r
        if bb.height > 30:
            return bb
    return pymupdf.Rect(page.rect.x0 + 40, cap_y1, page.rect.x1 - 40, min(next_y, cap_y1 + 320))


def split_lines(header: list[str], body: list[str], limit: int = MAX_CHARS) -> list[list[str]]:
    parts, cur = [], []
    base = sum(len(h) + 1 for h in header)
    for ln in body:
        if cur and base + sum(len(x) + 1 for x in cur) + len(ln) > limit:
            parts.append(cur)
            cur = []
        cur.append(ln)
    if cur or not parts:
        parts.append(cur)
    return parts


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--no-gemini", action="store_true", help="bỏ qua mô tả hình (debug)")
    args = ap.parse_args()
    load_env()
    from .config import DOC_TITLE
    gem = None
    if not args.no_gemini:
        from .gemini import VisionWithFallback
        gem = VisionWithFallback()
    t0 = time.perf_counter()
    doc = pymupdf.open(PDF_PATH)
    FIG_DIR.mkdir(parents=True, exist_ok=True)
    chunks, figures, pages_out, log = [], [], [], {"skipped_pages": sorted(SKIP_PAGES), "errors": []}
    section = None
    table_titles: dict[str, str] = {}
    counters: dict[str, int] = {}

    def add(kind: str, pdf_page: int, text: str, **meta) -> None:
        n = counters.get(f"{pdf_page}:{kind}", 0)
        counters[f"{pdf_page}:{kind}"] = n + 1
        chunks.append({"id": f"{DOC_ID}:p{pdf_page:03d}:{kind}:{n}", "text": text.strip(),
                       "source_id": DOC_ID, "source": DOC_TITLE, "page": pdf_page,
                       "metadata": {"pdf_page": pdf_page, "printed_page": pdf_page - PRINTED_OFFSET,
                                    "pages": [pdf_page], "kind": kind, "section": section, **meta}})

    for pno in range(1, doc.page_count + 1):
        page = doc[pno - 1]
        lines = page_lines(page)
        pages_out.append({"pdf_page": pno, "printed_page": pno - PRINTED_OFFSET,
                          "text": "\n".join(ln["text"] for ln in lines)})
        if pno in SKIP_PAGES:
            continue
        printed = pno - PRINTED_OFFSET
        img_area = sum(pymupdf.Rect(i["bbox"]).get_area() for i in page.get_image_info())
        text_chars = sum(len(ln["text"]) for ln in lines)

        # Questionnaire / full-page image pages → Gemini transcription
        if img_area > 0.5 * page.rect.get_area() and text_chars < 200:
            if gem:
                png = page.get_pixmap(dpi=130).tobytes("png")
                try:
                    res = gem.describe(png, FORM_PROMPT.format(title=DOC_TITLE, printed=printed))
                    add("form", pno, f"[Phiếu điều tra – trang {printed}]\n{res['text']}",
                        caption=f"Phiếu điều tra, trang {printed}", bbox=list(page.rect),
                        extracted_by=res["model_version"])
                except Exception as e:
                    log["errors"].append({"page": pno, "error": str(e)})
            continue

        # Split page into units at captions
        units: list[dict] = []
        cur = {"kind": "text", "caption": None, "lines": [], "section": section}
        i = 0
        while i < len(lines):
            ln = lines[i]
            t = ln["text"]
            plain = t.replace(" | ", " ")
            if HEAD_RE.match(plain) and len(plain) < 75 and not is_numeric_row(t):
                section = plain
            fm, tm = FIG_RE.match(plain), TAB_RE.match(plain)
            if fm:
                units.append(cur)
                cap_lines = [plain]
                j = i + 1  # caption may wrap onto the next line
                while j < len(lines) and lines[j]["y0"] - lines[j - 1]["y1"] < 4 and len(cap_lines) < 3 \
                        and not is_numeric_row(lines[j]["text"]) and len(lines[j]["text"]) < 90:
                    cap_lines.append(lines[j]["text"].replace(" | ", " "))
                    j += 1
                cap_y1 = lines[j - 1]["y1"]
                nxt = next((x["y0"] for x in lines[j:] if FIG_RE.match(x["text"]) or TAB_RE.match(x["text"])),
                           page.rect.y1 - 30)
                bb = figure_bbox(page, cap_y1, nxt)
                inside = [x["text"] for x in lines[j:] if x["y0"] >= cap_y1 - 1 and x["y1"] <= bb.y1 + 2]
                units.append({"kind": "figure", "caption": " ".join(cap_lines), "lines": inside,
                              "bbox": bb, "cap_y0": ln["y0"], "fig_no": fm.group(1), "section": section})
                i = j + len(inside)
                cur = {"kind": "text", "caption": None, "lines": [], "section": section}
                continue
            if tm and (tm.group(2) or ":" in plain[:12] or re.fullmatch(r"Biểu\s*\d+", plain.strip())):
                units.append(cur)
                cur = {"kind": "table", "caption": plain, "lines": [], "table_no": tm.group(1),
                       "cont": bool(tm.group(2)), "section": section}
                i += 1
                continue
            if cur["kind"] == "table" and not is_numeric_row(t) and "|" not in t and len(plain) > 75 \
                    and cur["lines"] and any(is_numeric_row(x) for x in cur["lines"]):
                units.append(cur)
                cur = {"kind": "text", "caption": None, "lines": [], "section": section}
            cur["lines"].append(t)
            i += 1
        units.append(cur)

        for u in units:
            if not u["lines"] and u["kind"] != "figure":
                continue
            sec = u.get("section")
            if u["kind"] == "text":
                body = [x.replace(" | ", " ") for x in u["lines"]]
                head = [f"[{sec}]"] if sec else []
                for part in split_lines(head, body):
                    if sum(len(x) for x in part) > 40:
                        add("text", pno, "\n".join(head + part))
            elif u["kind"] == "table":
                no = u["table_no"]
                rows = u["lines"]
                # Title continuation: wrapped caption (starts lowercase / "và", "chia"…) or the
                # all-caps title line(s) of Part III tables. Then the unit line and column headers.
                k = 0
                cont_lines = []
                while k < len(rows) and len(cont_lines) < 3 and "|" not in rows[k] and "Đơn vị" not in rows[k] \
                        and (rows[k][:1].islower() or UPPER_RE.match(rows[k])):
                    cont_lines.append(rows[k])
                    k += 1
                header_lines = []
                while k < len(rows) and not is_numeric_row(rows[k]) and len(header_lines) < 8:
                    header_lines.append(rows[k])
                    k += 1
                if not u["cont"]:
                    table_titles[no] = " ".join([u["caption"]] + cont_lines)
                title = table_titles.get(no, " ".join([u["caption"]] + cont_lines))
                header = [title + (" (Tiếp theo)" if u["cont"] else "")] + header_lines
                body = rows[k:]
                for part in split_lines(header, body):
                    add("table", pno, "\n".join(header + part), caption=title, table_no=no)
            elif u["kind"] == "figure":
                bb = u["bbox"]
                crop = pymupdf.Rect(page.rect.x0 + 20, u["cap_y0"] - 4, page.rect.x1 - 20, bb.y1 + 6)
                png_path = FIG_DIR / f"hinh_{u['fig_no'].replace('.', '_')}_p{pno:03d}.png"
                pix = page.get_pixmap(dpi=150, clip=crop)
                pix.save(png_path)
                desc, model_version = "", None
                if gem:
                    try:
                        res = gem.describe(pix.tobytes("png"), FIG_PROMPT.format(
                            title=DOC_TITLE, printed=printed, caption=u["caption"]))
                        desc, model_version = res["text"], res["model_version"]
                    except Exception as e:
                        log["errors"].append({"page": pno, "figure": u["fig_no"], "error": str(e)})
                labels = " ".join(x.replace(" | ", " ") for x in u["lines"])
                text = (f"{u['caption']}\n[Mô tả hình do vision model trích xuất]\n{desc}"
                        + (f"\n[Nhãn chữ trong hình]: {labels}" if labels else ""))
                fig = {"fig_no": u["fig_no"], "caption": u["caption"], "pdf_page": pno, "printed_page": printed,
                       "bbox": [round(v, 1) for v in bb], "crop": str(png_path.relative_to(BUILD)),
                       "extracted_by": model_version}
                figures.append(fig)
                add("figure", pno, text, caption=u["caption"], fig_no=u["fig_no"], bbox=fig["bbox"],
                    crop=fig["crop"], extracted_by=model_version)

    write_json(BUILD / "pages.json", pages_out)
    write_json(BUILD / "chunks.json", chunks)
    write_json(BUILD / "figures.json", figures)
    kinds = {}
    for c in chunks:
        kinds[c["metadata"]["kind"]] = kinds.get(c["metadata"]["kind"], 0) + 1
    log.update({"pdf": str(PDF_PATH.name), "pages": doc.page_count, "chunks": len(chunks), "by_kind": kinds,
                "figures": len(figures), "tables": len(table_titles),
                "max_chunk_chars": max(len(c["text"]) for c in chunks),
                "seconds": round(time.perf_counter() - t0, 1)})
    if gem:
        log["vision"] = gem.stats()
    write_json(BUILD / "ingest_log.json", log)
    print(json.dumps(log, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
