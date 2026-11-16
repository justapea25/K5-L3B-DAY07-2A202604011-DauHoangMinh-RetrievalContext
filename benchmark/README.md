# Benchmark Day 7 — Bộ luật Lao động 2019

`questions.json` được sinh bởi `python -m src.prepare_data` từ:
- **q01–q20**: benchmark Day 6 (15 dev / 5 test). Test Day 6 chỉ chạy một lần sau khi chốt cấu hình Day 6, không dùng để chỉnh → giữ làm test.
- **q21–q26, u01–u04**: thêm ở Day 7 (`extra_questions.json`), viết **trước** mọi thí nghiệm Day 7.

| Split | Có đáp án | Thiếu evidence | Multi-hop (trong số có đáp án) |
|---|---:|---:|---:|
| dev | 20 | 2 (u01, u02) | 2 (q24, q25) |
| test | 6 | 2 (u03, u04) | 1 (q26) |

## Schema & định nghĩa hit

- `gold_groups`: danh sách **nhóm evidence bắt buộc**; mỗi nhóm là danh sách evidence thay thế `{source_id, page, article, evidence}`. Câu thường có 1 nhóm; multi-hop có 2 nhóm.
- Trang của evidence được tìm tự động trong văn bản chuẩn hóa Day 6 (`pages.jsonl`) và kiểm tra lại `article`; script dừng nếu evidence không nằm trọn trong một chunk của đúng Điều/trang.
- **Hit** của một chunk: cùng `source_id`, trang evidence ∈ `metadata.pages` của chunk, evidence (chuẩn hóa khoảng trắng) nằm trọn trong text.
- Hit@1 / Evidence Hit@3: top-k chứa evidence của **ít nhất một** nhóm (định nghĩa Day 6). Full Hit@3 / Context Evidence: **mọi** nhóm.
- Câu thiếu evidence không vào mẫu số retrieval metrics. Lý do thiếu và cách kiểm tra ghi trong `absence_reason` (tìm từ khóa trên toàn văn bản, không dựa vào top-k).
- `filter` (chỉ `chapter`) là phạm vi người hỏi nêu trong câu (q12–q14, q20), giữ nguyên từ Day 6; không suy từ gold.

## Tiêu chí chọn cấu hình agent (chốt trên dev, trước khi chạy test)

Ghi sau khi xem kết quả dev vòng 2, **trước** khi chạy bất kỳ câu test nào của Day 7. Thứ tự ưu tiên:

1. Từ chối sai trên câu có đáp án (thấp hơn tốt hơn) — và phải từ chối đúng 2/2 câu thiếu evidence.
2. Agent Context Evidence Rate (context cuối chứa đủ mọi nhóm evidence).
3. Tỷ lệ citation có chứa evidence chuẩn (proxy tự động, không thay chấm tay).
4. Chi phí token, rồi latency trung vị.

Kết quả dev (`results/agent/dev/*/summary_auto.json`): bốn cấu hình hòa ở (1) 0/20 và (2) 19/20;
ở (3) hai cấu hình `*_budget_alias` đạt 21/23 so với 20/23; ở (4) hybrid 0,0089 USD < dense 0,0106 USD.

**Cấu hình chọn: `agent_hybrid_multi_budget_alias`** (hybrid RRF dense+BM25 bigram, top-3 mỗi lượt,
tối đa 4 lượt tìm, budget 8000 ký tự, policy `best_rank`, citation nhãn `[S#]`).
**Baseline so sánh trên test: `agent_dense_single`** (dense top-3, 1 lượt tìm, budget 4000, `first_come`).

Lưu ý: dev gần trần với các proxy này và có dao động giữa các lần chạy (ví dụ `agent_hybrid_multi`
19/20 ở vòng 1, 20/20 ở vòng 2 dù code retrieval/agent không đổi ngoài tiêu đề đoạn), nên chênh lệch nhỏ giữa
các cấu hình top không có ý nghĩa thống kê mạnh.
