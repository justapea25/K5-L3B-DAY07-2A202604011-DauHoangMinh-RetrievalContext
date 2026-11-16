# Báo cáo Day 7 — Đậu Hoàng Minh (2A202604011)

Agentic RAG tra cứu Bộ luật Lao động 2019: agent gpt-4o-mini (tool calling), 3 phương pháp retrieval (dense trên pgvector Day 6, BM25, hybrid RRF). Cách chạy và chi tiết hệ thống: [src/README.md](../../src/README.md). Benchmark và tiêu chí chọn: [benchmark/README.md](../../benchmark/README.md).

**Kết luận:** trên dev, tìm nhiều lượt + hybrid + citation nhãn ngắn giảm từ chối nhầm **4/20 → 0/20** với chi phí gần như không đổi. Trên test, cấu hình chọn và baseline **hòa 1,67/2**: baseline thiếu một ý multi-hop (q26), cấu hình chọn tính sai (q18). Lỗi còn lại nằm ở khâu model (bịa ID, chọn nhầm Điều, tính sai), không ở khâu tìm.

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk:** Bộ luật Lao động 45/2019/QH14 (bản gốc khi ban hành), PDF 47 trang (46 trang nội dung); văn bản quy phạm pháp luật không thuộc đối tượng bảo hộ quyền tác giả nên corpus nộp kèm tại [data/day7/chunks.json](../../data/day7/chunks.json). Gồm 252 chunk (strategy B Day 6: mỗi Điều 1 chunk, tối đa 1.500 ký tự).
- **Vector store, embedding model, phiên bản và số chiều:** PostgreSQL 16 + pgvector 0.8.7 của Day 6; `intfloat/multilingual-e5-small`, 384 chiều, cosine exact. Đã kiểm tra: tính lại vector của một chunk, cosine với vector đã lưu = 1,0000.
- **Agent model, cách chạy và phân chia dev/test:** `gpt-4o-mini`, temperature 0. Chạy: `src.prepare_data` → `src.eval_retrieval` → `src.run_agent` → `src.grade`.
  - Dev: 20 câu có đáp án + 2 câu thiếu evidence. Test: 6 + 2.
  - q01–q20 lấy từ Day 6; 10 câu mới viết trước mọi thí nghiệm (3 câu multi-hop, 4 câu thiếu evidence).
  - Test chỉ dùng các Điều không có trong dev.
- **Cách xác định câu có/thiếu evidence và tiêu chí chấm:**
  - Câu có đáp án: evidence ghi nguyên văn trong `gold_groups` (nhóm bắt buộc, mỗi nhóm có thể có evidence thay thế). Script tự kiểm tra evidence nằm trọn trong chunk đúng Điều và đúng trang.
  - Câu thiếu evidence: kiểm tra bằng tìm từ khóa trên toàn văn bản, không dựa vào top-k.
  - Câu trả lời chấm 0/1/2, citation có hỗ trợ hay không, và abstention, theo [BENCHMARK.md](../../BENCHMARK.md).

## Retrieval và thử nghiệm

**3 phương pháp:**

- Dense: pgvector.
- BM25: âm tiết + bigram (`thử_việc`).
- Hybrid: RRF, mỗi bên lấy top-20, k = 60.

**Cách đo:**

- Hit@1 và Evidence Hit@3 đo trên câu hỏi gốc, một lượt tìm.
- Context Evidence đo trên context cuối agent gửi cho model, phải đủ mọi nhóm evidence.
- Filter `chapter` chỉ lấy từ phạm vi người hỏi nêu (q12–q14, q20).

| Cấu hình                                        | Phương pháp, top-k, filter, rerank, context budget                                   | Giả thuyết / thay đổi                            | Split | Hit@1        | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí           |
| ------------------------------------------------- | --------------------------------------------------------------------------------------- | ---------------------------------------------------- | ----- | ------------ | -------------- | --------------------- | ------------------------------- |
| Baseline `agent_dense_single`                   | Dense top-3, filter người dùng, không rerank, 4000 ký tự `first_come`, 1 lượt | RAG một lượt (Day 6 + LLM)                        | dev   | 18/20 = 0,90 | 20/20 = 1,00   | 17/20 = 0,85          | 2,98 s/câu; 0,0077 USD/22 câu |
| Phương pháp 2 `bm25_bigram_k3`               | BM25 âm tiết + bigram, top-3 (chỉ retrieval)                                         | Bắt thuật ngữ trùng văn bản                    | dev   | 17/20 = 0,85 | 19/20 = 0,95   | 19/20 = 0,95          | 0,8 ms; 0 USD                   |
| Phương pháp 3 `agent_hybrid_multi`           | Hybrid RRF, top-3, 4000 `first_come`, ≤ 4 lượt                                     | Bổ sung khớp thuật ngữ cho câu diễn đạt lại | dev   | 18/20 = 0,90 | 20/20 = 1,00   | 19/20 = 0,95          | 2,67 s; 0,0087 USD              |
| Cải thiện 1 `agent_dense_multi`               | Dense, ≤ 4 lượt                                                                      | Tìm nhiều lượt cho câu multi-hop                | dev   | 18/20        | 20/20          | 18/20 = 0,90          | 2,74 s; 0,0124 USD              |
| Cải thiện 2 `agent_hybrid_multi_budget`       | Hybrid, 8000 ký tự `best_rank`                                                      | Evidence bị loại vì budget (q11, q25)             | dev   | 18/20        | 20/20          | 19/20 = 0,95          | 2,59 s; 0,0095 USD              |
| Cải thiện 3 `agent_hybrid_multi_budget_alias` | + citation nhãn `[S#]`                                                               | Model bịa chunk ID (q12, q15, q21)                  | dev   | 18/20        | 20/20          | 19/20 = 0,95          | 2,38 s; 0,0089 USD              |
| Cấu hình đã chọn (như cải thiện 3)        | như trên                                                                              | Chốt trên dev trước khi chạy test               | test  | 6/6 = 1,00   | 6/6 = 1,00     | 6/6 = 1,00            | 3,27 s; 0,0058 USD/8 câu       |
| Baseline                                          | như trên                                                                              |                                                      | test  | 6/6 = 1,00   | 6/6 = 1,00     | 5/6 = 0,83            | 2,68 s; 0,0026 USD/8 câu       |

**Ghi chú về bảng:**

- BM25 chỉ tách âm tiết (không bigram) đạt Hit@1 16/20, kém bigram.
- Dense top-5 với budget 6000 đạt Context Evidence 20/20.
- Bỏ filter không đổi điểm.
- Đối chứng dense + alias: 19/20, chi phí 0,0106 USD.
- Chi tiết: [results/retrieval/dev/summary.json](../../results/retrieval/dev/summary.json).

**Hai lỗi dev** (vòng 1 ở [dev_round1/](../../results/agent/dev_round1/); vòng 2 chạy lại cả 6 cấu hình trên cùng một phiên bản code):

1. **Bịa citation ID (q12, q15, q21).**
   - Hiện tượng: model trả lời đúng nhưng trích `art137:4`, trong khi chỉ có `art137:0` và `art137:1`, vì hiểu hậu tố của chunk ID là số khoản. Validator loại citation sai, câu thành từ chối nhầm.
   - Cách thử: đổi sang nhãn `[S1]`, `[S2]`, khi sửa thì cho model biết danh sách nhãn hợp lệ.
   - Kết quả: từ chối nhầm 3/20 → 0/20.
   - Giới hạn: việc thêm "Điều N" vào tiêu đề đoạn context cũng góp phần, nên không tách riêng được tác dụng của nhãn alias.
2. **Thiếu evidence trong context (q24, q11, q25).**
   - Hiện tượng: chỉ tìm 1 lượt nên thiếu một ý multi-hop (q24); budget 4000 kiểu `first_come` đã đầy nên Điều 114 tìm được ở lượt 3 không vào được context (q11).
   - Cách thử: cho ≤ 4 lượt tìm, budget 8000 kiểu `best_rank`, dùng hybrid.
   - Kết quả: Context Evidence của agent 17/20 → 19/20.

**Lỗi chưa sửa:** ở q25, mọi cấu hình đều trích Điều 36 (người sử dụng lao động báo trước 45 ngày) thay vì Điều 35 (người lao động báo trước), vì con số trùng nhau.

**Lý do chọn:** tiêu chí ghi trước khi chạy test, xét theo thứ tự: ít từ chối nhầm nhất → Context Evidence → citation chứa evidence → chi phí.

- Bốn cấu hình hòa ở hai tiêu chí đầu.
- Hai cấu hình alias thắng ở tiêu chí citation (21/23).
- Hybrid rẻ hơn dense.

→ Chọn **`agent_hybrid_multi_budget_alias`**. Dù temperature = 0, kết quả vẫn dao động khoảng 1 câu giữa các lần chạy, nên chênh lệch nhỏ giữa các cấu hình dẫn đầu không đủ để kết luận.

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi** ([src/agent.py](../../src/agent.py)):
  - Tool: `search_law`, `answer`, `abstain` (bắt buộc gọi tool mỗi lượt).
  - Context: bỏ trùng, giới hạn budget ký tự, chính sách `best_rank`.
  - Dừng khi:
    - model gọi `answer` hoặc `abstain`;
    - hết lượt tìm (gỡ tool tìm kiếm);
    - quá 8 lượt gọi model;
    - citation không có trong context (cho sửa 1 lần rồi chuyển thành từ chối).
  - Lỗi API ghi `status: error`, không thay bằng kết quả giả. Một lần mất mạng khi chạy dev được giữ lại ở [dev_connection_errors/](../../results/agent/dev_connection_errors/).

| Cấu hình / split                                     | Tool use | Số lượt gọi                             | Grounded answer 0/1/2 và trung bình | Citation hợp lệ    | Câu có citation | Abstention đúng | Từ chối nhầm |
| ------------------------------------------------------ | -------- | ------------------------------------------- | ------------------------------------- | -------------------- | ----------------- | ----------------- | --------------- |
| `agent_hybrid_multi_budget_alias` / test             | 8/8      | Lượt tìm 1–4 (TB 1,75); gọi model 2–5 | 1/0/5, **1,67**                 | 6/7                  | 6/6               | 2/2               | 0/6             |
| `agent_dense_single` / test                          | 8/8      | 1 lượt tìm; 2 lần gọi model            | 1/0/5, **1,67**                 | 5/5                  | 5/5               | 2/2               | 1/6             |
| `agent_hybrid_multi_budget_alias` / dev (tự động) | 22/22    | TB 1,18 lượt tìm                         | — (trả lời 20/20)                  | 21/23 chứa evidence | 20/20             | 2/2               | 0/20            |
| `agent_dense_single` / dev (tự động)              | 22/22    | 1 lượt tìm                               | — (trả lời 16/20)                  | 16/18 chứa evidence | 16/16             | 2/2               | 4/20            |

| Query ID | Loại câu          | Tool call và kết quả               | Câu trả lời và citation                                                          | Nhãn, lý do                                                          |
| -------- | ------------------- | ------------------------------------- | ------------------------------------------------------------------------------------ | ---------------------------------------------------------------------- |
| q16      | Có điều kiện    | 1 lượt, Điều 46 hạng 1           | Một nửa tháng lương/năm, khi làm đủ 12 tháng; `art046:0`                 | 2, ✓. Ngoại lệ diễn đạt chung hơn nguyên văn                  |
| q17      | Có điều kiện    | 1 lượt, Điều 128                  | 15 ngày (đặc biệt ≤ 90), tạm ứng 50%; `art128:0`                            | 2, ✓                                                                  |
| q18      | Diễn đạt lại    | 1 lượt, Điều 139 hạng 1          | "08 tháng… 06 + 01 = 07… 08 tháng"; `art139:0`                                 | **0**, ✗: đúng là 7 tháng, tự mâu thuẫn. Baseline đúng |
| q19      | Diễn đạt lại    | 1 lượt, Điều 115                  | Kết hôn nghỉ 03 ngày; `art115:0`                                               | 2, ✓                                                                  |
| q20      | Filter chương XIV | 1 lượt có lọc, Điều 190         | 06 tháng kể từ ngày phát hiện; `art190:0`                                    | 2, ✓                                                                  |
| q26      | Multi-hop           | 2 lượt: Điều 139, rồi Điều 140 | 06 tháng `[art139]`; bố trí việc khác, lương không thấp hơn `[art140]` | 2, ✓✓. Baseline 1 lượt → từ chối (0)                            |
| u03      | Thiếu evidence     | 4 lượt, có Điều 217              | Từ chối: không có mức phạt                                                     | Từ chối đúng                                                       |
| u04      | Thiếu evidence     | 3 lượt                              | Từ chối                                                                            | Từ chối đúng                                                       |

- **Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:**
  - Trace: `results/agent/<split>/<config>/traces.json`.
  - Nhãn: `results/agent/test/<config>/reviews.json`, phiếu chấm `review_sheet.md`, tổng hợp `summary_human.json`.
  - Tổng chi phí khoảng **0,108 USD** (giá 0,15 / 0,60 USD cho mỗi 1M token vào/ra); retrieval chạy local, 0 USD.
- **Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:**
  - **Ví dụ:**
    - Có bằng chứng: q26, agent tự tách thành 2 lượt tìm.
    - Thiếu bằng chứng: u04, từ chối, không bịa.
    - Lỗi: q18, mọi chỉ số tự động đều "tốt" nhưng đáp án sai; chỉ chấm tay mới thấy. Lỗi này thấy trên test nên không dùng để chỉnh hệ thống.
  - **Đánh đổi:** tìm nhiều lượt làm token tăng (dense_multi 71k so với 41k token). Hybrid tìm trúng sớm hơn nên rẻ hơn dense. Trên test, cấu hình chọn tốn khoảng 2,2 lần baseline, chủ yếu vì tìm 3–4 lượt trước khi từ chối.
  - **Giới hạn:**
    - Test chỉ có 6 câu có đáp án (mỗi câu = 17 điểm phần trăm).
    - Retrieval gần trần nên khác biệt chủ yếu thấy ở agent.
    - Kết quả dao động giữa các lần chạy.
    - Nhãn alias không bắt buộc citation ngay sau từng ý.
    - Corpus là bản gốc 2019, chưa có các sửa đổi sau này.
  - **Hướng tiếp theo** (thử trên dev): tự kiểm tra phép tính và chủ thể trước khi trả lời; rerank để phân biệt Điều 35 và Điều 36.

## Thử thách nâng cao (nếu thực hiện)

- Cách chạy: [advanced/README.md](../../advanced/README.md)
- Benchmark: [advanced/benchmark/questions.json](../../advanced/benchmark/questions.json)
- Kết quả: [advanced/results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/](../../advanced/results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/)
- **Tài liệu, nguồn, quyền sử dụng, số trang và phiên bản:**

  - *Kết quả chủ yếu Điều tra biến động dân số và KHHGĐ thời điểm 01/4/2025* (Cục Thống kê), 237 trang.
  - Trang công bố: [https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/08/ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-va-ke-hoach-hoa-gia-dinh-thoi-diem-01-4-2025/](https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/08/ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-va-ke-hoach-hoa-gia-dinh-thoi-diem-01-4-2025/)
  - File PDF: [https://www.nso.gov.vn/wp-content/uploads/2026/08/Sach-ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-2025.-pdf.pdf](https://www.nso.gov.vn/wp-content/uploads/2026/08/Sach-ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-2025.-pdf.pdf)
  - SHA-256: `d2178d7b8fb71699c67eed4c4382d10c8658ea0bca06793ae4d2abeee706c2fe`
- **Cách xử lý text, bảng, ảnh, biểu đồ; phạm vi index và phần chưa xử lý:**

  - Index toàn bộ 233 trang có nội dung (bỏ 4 trang bìa), được 490 chunk.
  - **Text** (219 chunk) và **bảng** (245 chunk, 70 biểu): trích bằng PyMuPDF, dựng lại hàng/cột theo tọa độ chữ (`a | b | c`), mỗi chunk lặp lại tiêu đề bảng và đơn vị.
  - **14 biểu đồ**: tìm vùng ảnh (bbox), cắt ở 150 dpi, cho Gemini (vision) mô tả và liệt kê nhãn số.
  - **12 trang phiếu điều tra dạng ảnh**: Gemini chép lại theo dạng "phương án = mã → câu chuyển tới".
- **Cách chia benchmark, schema evidence, model và cấu hình đã chốt trên dev:**

  - Dev 18 câu (15 có đáp án, 3 thiếu evidence). Test 30 câu (24 + 6), `split = test_v2`.
  - `gold` là danh sách nhóm evidence bắt buộc (VÀ). Mỗi nhóm gồm các evidence thay thế (HOẶC), dạng `{trang PDF, loại chunk, chuỗi evidence}`.
  - Câu biểu đồ và câu phiếu phải trích đúng chunk hình/phiếu, có bbox.
  - `python -m advanced.run --validate` kiểm tra mọi evidence có trong tài liệu, và mọi từ khóa của câu thiếu evidence đều không có trong 490 chunk.
  - Chấm:
    - Tự động (proxy): đạt khi trả lời và trích đúng chunk gold → 24/30.
    - Chính thức: chấm tay từng câu, đối chiếu PDF gốc; câu ranh giới tính là trượt → **27/30**.
    - Auto thấp hơn vì v04, v21, v22 trả lời đúng nhưng trích đoạn văn có cùng số liệu, không trích chunk bảng trong gold.
  - Agent `adv_hybrid_multi_v4`: hybrid RRF top-4, tối đa 4 lượt tìm, budget 12.000 ký tự, nhãn `[S#]`, thêm tool `calculator` và `search_form`, không cho từ chối khi mới tìm dưới 2 lượt. Model **gpt-6-luna**.
  - Kết quả dev (chấm tự động): **17/18**, 0 lỗi, latency trung vị 3,4 s/câu, khoảng 149k token vào, 2,7k token ra, chi phí **0,0162 USD**/18 câu. Kết quả: [advanced/results/dev/adv_hybrid_multi_v4_gpt-6-luna/](../../advanced/results/dev/adv_hybrid_multi_v4_gpt-6-luna/)

    | Nhóm dev | Bảng | Ảnh, sơ đồ | Biểu đồ | Multi-hop | Text | Thiếu bằng chứng |
    |---|---|---|---|---|---|---|
    | Đạt (auto) | 4/4 | 3/3 | 3/3 | 1/2 | 3/3 | 3/3 |

    - Câu duy nhất trượt auto là ad13: đáp án đúng (13,2% và 63,5%), nhưng trích Biểu 1.4 có cùng số "63,5" thay vì đoạn văn ghi trong gold.

| Nhóm test                         | Đạt / tổng   | Tỷ lệ       | Lỗi / nhận xét                                                                                                                             |
| ---------------------------------- | --------------- | ------------- | --------------------------------------------------------------------------------------------------------------------------------------------- |
| Bảng                              | 6/6             | 100%          |                                                                                                                                               |
| Ảnh, sơ đồ (phiếu điều tra) | 5/5             | 100%          |                                                                                                                                               |
| Biểu đồ                         | 3/5             | 60%           | v08 sai đỉnh (ghi "35–39 và 40–44"); v07 đúng nhưng trích đoạn văn mô tả hình thay vì vùng hình (ranh giới, chấm trượt) |
| Multi-hop                          | 3/4             | 75%           | v24 dùng số làm tròn "13,8 triệu" thay vì 13.775.109 (ranh giới, chấm trượt)                                                        |
| Text                               | 4/4             | 100%          |                                                                                                                                               |
| Thiếu bằng chứng                | 6/6             | 100%          | Từ chối đúng sau 2–3 lượt tìm                                                                                                         |
| **Toàn bộ**                | **27/30** | **90%** | Nếu tính 2 câu ranh giới là đạt: 29/30                                                                                                 |

- **Trace, nhãn và evidence từng câu; thời gian, chi phí, lỗi hệ thống:**
  - Trace từng câu: [advanced/results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/traces.json](../../advanced/results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/traces.json)
  - Nhãn và lý do từng câu: [advanced/results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/labels.json](../../advanced/results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/labels.json)
  - Tổng hợp theo nhóm: [advanced/results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/summary_auto.json](../../advanced/results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/summary_auto.json)
  - 0 lỗi hệ thống; latency trung vị 4,1 s/câu.
  - Chi phí, tính theo giá gpt-6-luna 0,10 / 0,50 USD cho mỗi 1M token vào/ra (giá chuẩn, không tính cache):

    | Bước | Token vào / ra | Chi phí |
    |---|---|---:|
    | Ingest: vision (Gemini) đọc 14 biểu đồ + 12 trang phiếu | | ~0,44 USD (chạy một lần, có cache) |
    | Agent trên dev, 18 câu | 148.716 / 2.744 | 0,0162 USD |
    | Agent trên test, 30 câu | 211.493 / 4.495 | 0,0234 USD (~0,0008 USD/câu) |
    | **Tổng** | | **~0,48 USD** |

    - Index (embedding e5-small, BM25) chạy local, 0 USD.
    - Token vào lớn gấp khoảng 47 lần token ra, vì mỗi lượt gửi lại context tới 12.000 ký tự (chunk bảng và phiếu dài 2–5k ký tự).
- **Giới hạn, cách tái lập và đường dẫn benchmark:**
  - Giới hạn:
    - **Biểu đồ là điểm yếu nhất (3/5):** 6 biểu đồ không ghi nhãn số chỉ được vision mô tả ở mức xu hướng, nên câu hỏi về đỉnh hoặc giá trị dễ sai (v08).
    - **Kết quả đúng bằng ngưỡng 90%** và phụ thuộc cách chấm 2 câu ranh giới (v07, v24); chỉ cần thêm 1 câu trượt là không đạt.
    - **Mỗi split chỉ chạy một lần:** model có dao động giữa các lần chạy, chưa đo độ lệch.
    - **Phụ thuộc vào bản chép của vision:** bản chép phiếu và mô tả hình do Gemini tạo; mới đối chiếu với ảnh gốc ở Hình 1.2 và các trang phiếu dùng trong benchmark, chưa kiểm tra hết 26 vùng ảnh.
    - **Chấm tự động thấp hơn thực tế:** proxy chỉ chấp nhận chunk ghi trong gold, nên câu trích nguồn khác có cùng số liệu bị tính trượt (dev ad13; test v04, v21, v22). Vì vậy kết quả chính thức dựa trên chấm tay.
    - **Benchmark nhỏ:** 30 câu test, mỗi câu bằng 3,3 điểm phần trăm; các nhóm có 4–6 câu nên tỷ lệ theo nhóm chưa ổn định.
  - Tái lập (chi tiết ở [advanced/README.md](../../advanced/README.md)):

    ```bash
    # cần OPENAI_API_KEY và GEMINI_API_KEY trong .env
    python -m advanced.fetch      # tải PDF + kiểm tra SHA-256
    python -m advanced.ingest     # chunk text/bảng/biểu đồ/phiếu → playground/advanced_build/
    python -m advanced.index      # index dense + BM25
    python -m advanced.run --validate
    python -m advanced.run --split dev     --only adv_hybrid_multi_v4_gpt-6-luna
    python -m advanced.run --split test_v2 --only adv_hybrid_multi_v4_gpt-6-luna
    ```

  - Benchmark: [advanced/benchmark/questions.json](../../advanced/benchmark/questions.json) (dev: `split = dev`, test: `split = test_v2`)

## Hỗ trợ của AI và trách nhiệm
