# Báo cáo Day 7 — Đậu Hoàng Minh (2A202604011)

Agentic RAG tra cứu Bộ luật Lao động 2019. Agent dùng model thật (gpt-4o-mini, tool calling) và được thử với ba phương pháp retrieval: dense trên pgvector Day 6, BM25 và hybrid RRF. Cách chạy và mô tả hệ thống: [src/README.md](../../src/README.md). Benchmark và tiêu chí chọn cấu hình: [benchmark/README.md](../../benchmark/README.md).

**Kết luận chính:**

- **Trên dev:** tìm nhiều lượt, dùng hybrid và đổi citation sang nhãn ngắn giúp giảm số câu bị từ chối nhầm từ **4/20 xuống 0/20**. Chi phí gần như không tăng: 0,0077 → 0,0089 USD cho 22 câu.
- **Trên test (6 câu có đáp án):** sau khi chấm tay, cấu hình đã chọn và baseline **hòa nhau, cùng 1,67/2**. Mỗi bên sai một câu, vì hai lý do khác nhau:
  - Baseline từ chối nhầm câu multi-hop q26, vì chỉ tìm một lượt.
  - Cấu hình đã chọn tìm đúng evidence nhưng tính sai ở q18.
- Phần lớn lỗi còn lại nằm ở khâu **model** (bịa ID citation, chọn nhầm Điều, tính sai), không nằm ở khâu tìm kiếm.

## Dữ liệu và benchmark

- **Nguồn, quyền sử dụng, số trang và số chunk:**
  - Bộ luật Lao động số 45/2019/QH14, bản gốc khi ban hành, không gồm các sửa đổi sau này. Đây là cùng file PDF và cùng cách chuẩn hóa ở Day 6.
  - PDF có 47 trang, trong đó 46 trang có nội dung. Nguồn và sha256 ghi trong báo cáo Day 6.
  - Văn bản quy phạm pháp luật không thuộc đối tượng bảo hộ quyền tác giả (khoản 1 Điều 15 Luật SHTT), nên corpus được đưa vào repo tại [data/day7/chunks.json](../../data/day7/chunks.json).
  - Corpus gồm **252 chunk**, dùng strategy B của Day 6: mỗi Điều một chunk, tối đa 1.500 ký tự; Điều dài được tách theo khoản và lặp lại tiêu đề Điều.
  - Metadata mỗi chunk: `pages` (mọi trang chunk chạm tới), `chapter`, `articles`, `content_hash`.
- **Vector store, embedding model, phiên bản và số chiều:**
  - Vector store: PostgreSQL 16 + pgvector 0.8.7 (Docker `pgvector/pgvector:0.8.7-pg16`). Dùng lại nguyên bảng `chunks` của Day 6 với `strategy = 'B'`, không index lại.
  - Embedding: `intfloat/multilingual-e5-small`, **384 chiều**, chuẩn hóa L2, tiền tố `query: ` cho câu hỏi và `passage: ` cho văn bản. Tìm kiếm bằng cosine, quét toàn bộ (exact), không dùng ANN. Chạy local trên CPU.
  - **Kiểm tra tương thích:** khi khởi tạo, code dừng với lỗi nếu số dòng, tên model hoặc số chiều trong DB khác với corpus. Ngoài ra đã tính lại vector của một chunk và so với vector đã lưu ở Day 6: cosine = 1,0000.
- **Agent model, cách chạy và phân chia dev/test:**
  - Model: `gpt-4o-mini` (API trả về `gpt-4o-mini-2024-07-18`), temperature 0, Python 3.12 
  - Lệnh chạy:

    - `python -m src.prepare_data`
    - `python -m src.eval_retrieval --split dev|test`
    - `python -m src.run_agent --split dev|test`
    - `python -m src.grade ...`
  - Chia dev/test:

    | Split | Có đáp án | Thiếu evidence | Tổng |
    | ----- | ------------: | --------------: | ----: |
    | dev   |            20 |               2 |    22 |
    | test  |             6 |               2 |     8 |
  - **q01–q20** lấy từ benchmark Day 6. Bộ test Day 6 (q16–q20) chỉ chạy một lần, chưa từng dùng để chỉnh hệ thống.
  - **q21–q26 và u01–u04** được viết thêm ở Day 7, trước mọi thí nghiệm. Gồm:

    - 3 câu diễn đạt lại / có điều kiện.
    - 3 câu multi-hop: q24 và q25 ở dev, q26 ở test.
    - 4 câu thiếu evidence.
  - Câu test chỉ dùng các Điều không xuất hiện trong dev: 46, 115, 128, 139, 140, 190.
- **Cách xác định câu có/thiếu evidence và tiêu chí chấm:**
  - **Câu có đáp án:** ghi nguyên văn evidence trong `gold_groups`, tức danh sách nhóm evidence **bắt buộc**; mỗi nhóm có thể gồm nhiều evidence thay thế nhau. Câu multi-hop có 2 nhóm.
    - `prepare_data` tự tìm trang của evidence trong văn bản chuẩn hóa từng trang, rồi kiểm tra evidence nằm trọn trong một chunk của đúng Điều. Không đạt thì script dừng với lỗi.
    - Một chunk được tính là **hit** khi: cùng nguồn, trang của evidence nằm trong `pages` của chunk, và evidence (đã chuẩn hóa khoảng trắng) nằm trọn trong text.
  - **Câu thiếu evidence:** đều là câu gần chủ đề, ví dụ mức lương tối thiểu vùng, mức trợ cấp thất nghiệp, mức phạt, kinh phí công đoàn. `absence_reason` ghi cách đã kiểm tra trên **toàn văn bản** (tìm từ khóa), không dựa vào top-k. Các câu này không vào mẫu số của chỉ số retrieval.
  - **Chấm câu trả lời:** theo [BENCHMARK.md](../../BENCHMARK.md), gồm điểm 0/1/2, citation có hỗ trợ không và abstention. Nhãn chấm tay chỉ áp dụng cho test (mục "Hỗ trợ của AI" ghi rõ ai làm gì).

## Retrieval và thử nghiệm

**Ba phương pháp retrieval:**

- **Dense:** truy vấn pgvector Day 6.
- **BM25:** Okapi, k1 = 1,5, b = 0,75, viết bằng Python thuần. Có hai cách tách từ: theo âm tiết, và theo âm tiết cộng thêm *bigram* (`thử_việc`) để xấp xỉ từ ghép tiếng Việt.
- **Hybrid:** Reciprocal Rank Fusion giữa dense và BM25-bigram (lấy top-20 mỗi bên, k = 60, trọng số 1:1). RRF dùng thứ hạng nên không phải cộng hai thang điểm khác nhau.

**Cách đo:**

- Query là câu hỏi gốc. Filter `chapter` chỉ lấy từ phạm vi người hỏi nêu (q12–q14, q20), không bao giờ từ gold.
- Hit@1 và Evidence Hit@3 đo trên kết quả retrieval của **câu hỏi gốc**, một lượt tìm (`results/retrieval/`).
- Context Evidence Rate đo trên **context cuối mà agent gửi cho model**: phải chứa đủ mọi nhóm evidence. Riêng các dòng chỉ chạy retrieval thì đo trên top-k sau khi cắt theo budget.

| Cấu hình                                                          | Phương pháp, top-k, filter, rerank, context budget                                                          | Giả thuyết / thay đổi                                      | Split | Hit@1        | Evidence Hit@3 | Context Evidence Rate | Thời gian / chi phí                         |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------- | ----- | ------------ | -------------- | --------------------- | --------------------------------------------- |
| Baseline `agent_dense_single`                                     | Dense, top-3, filter người dùng, không rerank, budget 4000 ký tự `first_come`, **1 lượt tìm** | RAG một lượt, giống Day 6 + LLM                            | dev   | 18/20 = 0,90 | 20/20 = 1,00   | 17/20 = 0,85 (agent)  | 2,98 s/câu (trung vị); 0,0077 USD / 22 câu |
| Phương pháp 2 `bm25_bigram_k3`                                 | BM25 âm tiết + bigram, top-3, filter, budget 4000 (chỉ retrieval)                                           | Từ khóa luật bắt tốt hơn khi cách hỏi trùng văn bản | dev   | 17/20 = 0,85 | 19/20 = 0,95   | 19/20 = 0,95 (top-3)  | 0,8 ms/truy vấn; 0 USD                       |
| (biến thể) `bm25_unigram_k3`                                    | BM25 chỉ âm tiết                                                                                            | Đối chứng cho cách tách từ                               | dev   | 16/20 = 0,80 | 19/20 = 0,95   | 18/20 = 0,90 (top-3)  | 0,5 ms; 0 USD                                 |
| Phương pháp 3 `agent_hybrid_multi`                             | Hybrid RRF, top-3, filter, budget 4000 `first_come`, tối đa 4 lượt                                       | Hybrid bổ sung khớp thuật ngữ cho câu diễn đạt lại    | dev   | 18/20 = 0,90 | 20/20 = 1,00   | 19/20 = 0,95 (agent)  | 2,67 s; 0,0087 USD                            |
| Cải thiện 1 `agent_dense_multi`                                 | Dense, top-3, budget 4000 `first_come`, **tối đa 4 lượt**                                          | Cho tìm nhiều lượt để tách câu multi-hop               | dev   | 18/20 = 0,90 | 20/20 = 1,00   | 18/20 = 0,90 (agent)  | 2,74 s; 0,0124 USD                            |
| Cải thiện 2 `agent_hybrid_multi_budget`                         | Hybrid, top-3, **budget 8000 `best_rank`**, 4 lượt                                                   | Evidence bị loại vì budget (q11, q25)                       | dev   | 18/20 = 0,90 | 20/20 = 1,00   | 19/20 = 0,95 (agent)  | 2,59 s; 0,0095 USD                            |
| Cải thiện 3 `agent_hybrid_multi_budget_alias`                   | Như cải thiện 2 + **citation nhãn `[S#]`**                                                         | Model bịa chunk ID theo số khoản (q12, q15, q21)            | dev   | 18/20 = 0,90 | 20/20 = 1,00   | 19/20 = 0,95 (agent)  | 2,38 s; 0,0089 USD                            |
| Đối chứng `agent_dense_multi_budget_alias`                     | Như cải thiện 3 nhưng dùng dense                                                                          | Tách riêng tác động của phương pháp retrieval         | dev   | 18/20 = 0,90 | 20/20 = 1,00   | 19/20 = 0,95 (agent)  | 2,70 s; 0,0106 USD                            |
| **Cấu hình đã chọn** `agent_hybrid_multi_budget_alias` | như trên                                                                                                     | Chốt trên dev trước khi chạy test                         | test  | 6/6 = 1,00   | 6/6 = 1,00     | 6/6 = 1,00 (agent)    | 3,27 s; 0,0058 USD / 8 câu                   |
| Baseline `agent_dense_single`                                     | như trên                                                                                                     |                                                                | test  | 6/6 = 1,00   | 6/6 = 1,00     | 5/6 = 0,83 (agent)    | 2,68 s; 0,0026 USD / 8 câu                   |

**Thí nghiệm retrieval phụ trên dev:**

- `dense_k5` / `hybrid_rrf_k5` (top-5, budget 6000): Context Evidence 20/20, tức tăng budget sửa được lỗi cắt mất evidence ở q25.
- `dense_k3_nofilter`: bằng điểm `dense_k3`. Bốn câu có filter đủ rõ để tìm đúng chương mà không cần lọc.
- Câu trượt Hit@1:
  - dense và hybrid: q04, q21.
  - BM25 bigram: thêm q11.
  - BM25 unigram: q02, q03, q08, q21.
- Toàn bộ chi tiết: [results/retrieval/dev/summary.json](../../results/retrieval/dev/summary.json).

**Lưu ý:** "Phương pháp 3" (hybrid trong agent) đồng thời là một cấu hình cải thiện, vì nó sửa được q11 và q21 so với dense cùng tham số. Trên test, mọi phương pháp retrieval đều đạt 6/6 nên test không phân biệt được các phương pháp.

### Hai lỗi dev, nguyên nhân, cách thử

Vòng 1 ([results/agent/dev_round1/](../../results/agent/dev_round1/)) dùng để đọc lỗi. Vòng 2 ([results/agent/dev/](../../results/agent/dev/)) chạy lại **cả 6 cấu hình trên cùng một phiên bản code** để so sánh công bằng.

**Lỗi 1 — trả lời đúng nhưng bịa citation ID (q12, q15, q21).**

- **Hiện tượng:** ở q12, model trả lời đúng "60 phút mỗi ngày, hưởng đủ lương" nhưng trích `bllđ-2019:B:art137:4`. Điều 137 chỉ có `art137:0` và `art137:1`. Ở q21, model trích `art036:2b` trong khi ID thật là `art036:1`.
- **Nguyên nhân:** model hiểu hậu tố `:0`, `:1` của chunk ID thành số khoản/điểm trong luật. Validator từ chối citation không có trong context, cho sửa một lần, model lặp lại đúng ID sai, và câu thành *từ chối nhầm*.
- **Cách thử:**
  - Thêm "Điều N" vào tiêu đề mỗi đoạn context.
  - Thêm chế độ `citation_mode = "alias"`: mỗi đoạn có nhãn `[S1]`, `[S2]`…, code ánh xạ nhãn về chunk ID trong kết quả. Khi phải sửa, model được nhận danh sách nhãn hợp lệ.
- **Trước → sau:**
  - Vòng 1: q12 sai ở cả 4 cấu hình.
  - Vòng 2: q12 và q21 đúng ở cả hai cấu hình alias.
  - Với dense: từ chối nhầm **3/20 (`dense_multi`) → 0/20 (`dense_multi_budget_alias`)**.
- **Giới hạn của kết luận:** việc thêm "Điều N" vào tiêu đề cũng có tác dụng. Ở vòng 2, `hybrid_multi` vẫn dùng ID gốc nhưng không còn bịa ID ở q12. Vì vậy không tách riêng được phần cải thiện do nhãn alias.

**Lỗi 2 — thiếu evidence trong context: một lượt tìm, budget `first_come` (q24, q11, q25).**

- **Hiện tượng:**
  - q24 (multi-hop): baseline chỉ tìm một lượt, context có Điều 98 nhưng thiếu Điều 106, nên từ chối.
  - q11: `dense_multi` đã tìm 4 lượt và lượt 3 có tìm ra Điều 114, nhưng budget 4000 đã đầy bởi các đoạn không liên quan từ lượt 1–2 (Điều 147, 219). Với `first_come`, Điều 114 không được thêm vào context.
  - q25: ở retrieval `dense_k3`, cả hai evidence nằm trong top-3 nhưng một đoạn bị cắt vì vượt budget.
- **Cách thử:**
  - Cho tối đa 4 lượt tìm.
  - Budget 8000 với chính sách `best_rank`: ưu tiên đoạn hạng 1 của mọi lượt tìm, rồi đến hạng 2, hạng 3.
  - Đổi sang hybrid.
- **Trước → sau:**
  - q24: baseline sai → mọi cấu hình nhiều lượt đều đúng.
  - q11: `dense_multi` sai → `dense_multi_budget_alias` đúng; hybrid đúng ở mọi cấu hình.
  - Context Evidence của agent: **17/20 → 19/20**.
  - Retrieval: `dense_k3` 19/20 → `dense_k5` 20/20.

**Lỗi chưa sửa được — q25 (multi-hop, dev):**

- Mọi cấu hình đều trả lời "báo trước ít nhất 45 ngày" nhưng trích **Điều 36** (thời hạn *người sử dụng lao động* phải báo trước), thay vì **Điều 35** (thời hạn *người lao động* phải báo trước). Con số trùng nên câu trả lời nghe đúng, nhưng nguồn sai chủ thể.
- Không thử sửa thêm, vì lỗi nằm ở việc model chọn nhầm đoạn trong context chứ không phải ở retrieval. Context Evidence của q25 bị tính là thiếu, vì Điều 35 không có trong context cuối ở cấu hình đã chọn.

### Lý do chọn cấu hình

Tiêu chí được ghi vào [benchmark/README.md](../../benchmark/README.md) **trước khi chạy test**, xét theo thứ tự:

1. Ít câu từ chối nhầm nhất, đồng thời phải từ chối đúng 2/2 câu thiếu evidence.
2. Agent Context Evidence Rate cao nhất.
3. Tỷ lệ citation chứa evidence chuẩn cao nhất (proxy tự động).
4. Chi phí thấp nhất, rồi latency thấp nhất.

Kết quả so sánh:

- Bốn cấu hình hòa ở tiêu chí 1 và 2 (0/20 từ chối nhầm, Context Evidence 19/20).
- Tiêu chí 3: hai cấu hình alias đạt 21/23, hai cấu hình còn lại 20/23.
- Tiêu chí 4: hybrid tốn 0,0089 USD, rẻ hơn dense (0,0106 USD), vì hybrid tìm trúng sớm hơn (trung bình 1,18 lượt so với 1,32).

→ **Chọn `agent_hybrid_multi_budget_alias`.** Baseline để so sánh trên test là `agent_dense_single`.

**Độ dao động:** dù temperature = 0, cùng cấu hình `hybrid_multi` cho 19/20 câu được trả lời ở vòng 1 và 20/20 ở vòng 2. Chênh lệch 1 câu giữa các cấu hình dẫn đầu vì vậy không đủ để khẳng định cấu hình nào thật sự tốt hơn.

## Agent và đánh giá

- **Tool, số lượt gọi, điều kiện dừng, cách chọn context và xử lý lỗi** ([src/agent.py](../../src/agent.py)):
  - **Tool:** `search_law(query)`, `answer(answer, citations[])`, `abstain(reason)`. Model bắt buộc gọi đúng 1 tool mỗi lượt (`tool_choice = required`).
  - **Context:** gộp chunk từ mọi lượt tìm, bỏ trùng, giới hạn `budget_chars`, chọn đoạn theo `first_come` hoặc `best_rank`. Mỗi lượt tìm, model nhận lại toàn bộ context đã tích lũy.
  - **Điều kiện dừng:**
    - Model gọi `answer` hoặc `abstain`.
    - Đạt `max_searches`: tool tìm kiếm bị gỡ, model buộc phải trả lời hoặc từ chối.
    - Đạt `max_steps = 8` lượt gọi model: chuyển thành từ chối.
    - Citation không có trong context: cho sửa một lần, sau đó chuyển thành từ chối.
  - **Xử lý lỗi:**
    - Lỗi truy xuất được ghi vào trace và báo cho model, không thay bằng kết quả giả.
    - Lỗi gọi API được ghi với `status: "error"`. Một lần chạy dev bị `APIConnectionError` do mất mạng; trace được giữ lại tại [results/agent/dev_connection_errors/](../../results/agent/dev_connection_errors/) và cấu hình đó được chạy lại.
  - **Bảo vệ:** system prompt quy định nội dung tài liệu là dữ liệu, không phải chỉ dẫn.

**Test (nhãn chấm tay):**

| Cấu hình / split                         | Tool use | Số lượt gọi                                                      | Grounded answer 0/1/2 và trung bình | Citation hợp lệ | Câu có citation | Abstention đúng | Từ chối nhầm |
| ------------------------------------------ | -------- | -------------------------------------------------------------------- | ------------------------------------- | ----------------- | ----------------- | ----------------- | --------------- |
| `agent_hybrid_multi_budget_alias` / test | 8/8      | Lượt tìm: 1×5, 2×1, 3×1, 4×1 câu. Gọi model: 2–5 lần/câu | 1/0/5, **1,67/2**               | 6/7 = 0,86        | 6/6               | 2/2               | 0/6             |
| `agent_dense_single` / test              | 8/8      | Lượt tìm: 1×8 câu. Gọi model: 2 lần/câu                      | 1/0/5, **1,67/2**               | 5/5 = 1,00        | 5/5               | 2/2               | 1/6             |

**Dev (chỉ số tự động, chưa chấm tay):**

| Cấu hình / split                        | Tool use | Số lượt gọi                     | Trả lời câu có đáp án | Citation chứa evidence chuẩn | Abstention đúng | Từ chối nhầm |
| ----------------------------------------- | -------- | ----------------------------------- | ---------------------------- | ------------------------------ | ----------------- | --------------- |
| `agent_dense_single` / dev              | 22/22    | Lượt tìm: 1×22 câu             | 16/20                        | 16/18                          | 2/2               | 4/20            |
| `agent_hybrid_multi_budget_alias` / dev | 22/22    | Lượt tìm: 1×19, 2×2, 3×1 câu | 20/20                        | 21/23                          | 2/2               | 0/20            |

**Chi tiết từng câu test của cấu hình đã chọn** (khác biệt so với baseline ghi trong cột cuối):

| Query ID | Loại câu            | Tool call và kết quả                                                        | Câu trả lời và citation                                                                                                                                           | Nhãn, lý do                                                                                                                                                                                                                     |
| -------- | --------------------- | ------------------------------------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| q16      | Có điều kiện      | 1 lượt: Điều 46 hạng 1                                                    | Một nửa tháng lương mỗi năm, áp dụng khi làm thường xuyên đủ 12 tháng; trích `art046:0`                                                            | **2**, citation ✓. Ngoại lệ được diễn đạt chung chung hơn nguyên văn ("điểm e khoản 1 Điều 36") nhưng không sai. Baseline cũng 2                                                                        |
| q17      | Có điều kiện      | 1 lượt: Điều 128 hạng 1                                                   | Tối đa 15 ngày, đặc biệt không quá 90 ngày; tạm ứng 50% lương; trích `art128:0`                                                                       | **2**, citation ✓, khớp khoản 2. Baseline 2                                                                                                                                                                              |
| q18      | Diễn đạt lại      | 1 lượt `nghỉ thai sản sinh đôi`: Điều 139 hạng 1                    | "tổng cộng **08 tháng** … 06 + 01 = 07 tháng … là 08 tháng"; trích `art139:0`                                                                        | **0**, citation ✗. Đáp án đúng là 6 + 1 = 7 tháng; câu trả lời tự mâu thuẫn. Đoạn trích mâu thuẫn với kết luận nên citation không hỗ trợ. **Baseline trả lời đúng 7 tháng (2 điểm)** |
| q19      | Diễn đạt lại      | 1 lượt: Điều 115 hạng 1                                                   | Kết hôn được nghỉ 03 ngày hưởng nguyên lương; trích `art115:0`                                                                                         | **2**, citation ✓. Baseline 2                                                                                                                                                                                              |
| q20      | Metadata filter (XIV) | 1 lượt, lọc chương XIV: Điều 190 hạng 1                                | Thời hiệu 06 tháng kể từ ngày phát hiện vi phạm; trích `art190:0`                                                                                         | **2**, citation ✓, khớp nguyên văn khoản 1. Baseline 2                                                                                                                                                                 |
| q26      | Multi-hop             | 2 lượt: lượt 1 ra Điều 139; lượt 2 ra Điều 140                       | 06 tháng, trước sinh không quá 02 tháng `[art139:0]`; nếu việc cũ không còn, công ty bố trí việc khác với lương không thấp hơn `[art140:0]` | **2**, 2 citation ✓, mỗi ý có citation riêng. **Baseline chỉ tìm 1 lượt, thiếu Điều 140, từ chối (0 điểm)**                                                                                           |
| u03      | Thiếu evidence       | 4 lượt; context có Điều 217 (chỉ nói "xử phạt vi phạm hành chính") | Từ chối: không có mức phạt cụ thể                                                                                                                             | **Từ chối đúng**, không nêu con số. Baseline: 1 lượt, từ chối đúng                                                                                                                                             |
| u04      | Thiếu evidence       | 3 lượt; không có đoạn nào về kinh phí công đoàn                    | Từ chối                                                                                                                                                             | **Từ chối đúng**. Baseline cũng đúng                                                                                                                                                                                 |

- **Đường dẫn trace, nhãn, lệnh chạy, thời gian và chi phí:**
  - Trace từng câu: `results/agent/<split>/<config>/traces.json`. Mỗi trace gồm từng tool call, query, top-k kèm score, rank và trang, context sau mỗi lượt, context cuối, câu trả lời, citation, lý do dừng, token, chi phí, thời gian và lỗi.
  - Nhãn: `results/agent/test/<config>/reviews.json`. Phiếu chấm có nguyên văn đoạn được trích: `review_sheet.md`. Tổng hợp bằng `starter/agent_metrics.py`: `summary_human.json`.
  - Lệnh chạy: xem [src/README.md](../../src/README.md) mục 3.
  - Chi phí thí nghiệm, tổng **≈ 0,108 USD**:

    | Lần chạy                        |  Chi phí |
    | --------------------------------- | --------: |
    | Dev vòng 1                       | 0,035 USD |
    | Dev vòng 2                       | 0,058 USD |
    | Lần chạy dev bị lỗi kết nối | 0,007 USD |
    | Test                              | 0,008 USD |

    Giá dùng để tính: 0,15 / 0,60 USD cho mỗi 1M token input / output.
  - Retrieval và embedding chạy local, 0 USD.
- **Kết quả trước/sau, ví dụ lỗi, đánh đổi và giới hạn:**
  - **Ví dụ trả lời có bằng chứng:** q26. Agent tự tách câu hỏi thành 2 lượt tìm và trích đúng Điều cho từng ý.
  - **Ví dụ thiếu bằng chứng:** u04. Agent tìm 3 lượt, không thấy thông tin, từ chối và không bịa tỷ lệ.
  - **Ví dụ lỗi:** q18. Retrieval đúng hạng 1, citation hợp lệ, citation chứa evidence chuẩn: mọi chỉ số tự động đều báo "tốt", nhưng đáp án sai. Lỗi này chỉ chấm tay mới phát hiện được. Baseline đọc cùng đoạn luật lại trả lời đúng, nên đây là lỗi suy luận ngẫu nhiên của model chứ không do cấu hình gây ra. Lỗi được phát hiện trên test nên **không** dùng để chỉnh hệ thống.
  - **Đánh đổi:**
    - Tìm nhiều lượt làm token đầu vào tăng, vì mỗi lần gọi model đều gửi lại toàn bộ context tích lũy. `dense_multi` tốn 71k token so với 41k của baseline, mà chỉ sửa được 1 câu.
    - Hybrid tìm trúng sớm hơn nên rẻ hơn dense ở cùng cấu hình.
    - Trên test, cấu hình đã chọn tốn gấp khoảng 2,2 lần baseline (0,0058 so với 0,0026 USD), chủ yếu vì tìm 3–4 lượt ở câu thiếu evidence trước khi từ chối. Latency trung vị 3,27 s so với 2,68 s.
  - **Giới hạn:**
    1. Test chỉ có 6 câu có đáp án; mỗi câu bằng 17 điểm phần trăm. Kết quả hòa 1,67 = 1,67 không cho phép kết luận cấu hình nào tốt hơn trên test.
    2. Retrieval gần đạt tối đa trên benchmark này (Hit@3 dense/hybrid 20/20 trên dev, 6/6 trên test), nên khác biệt giữa các phương pháp chủ yếu thấy được qua agent.
    3. Không tách riêng được tác động của budget 8000 vì hybrid đã tự sửa q11.
    4. Kết quả có dao động giữa các lần chạy dù temperature = 0.
    5. Chế độ alias chỉ bắt buộc danh sách `citations` hợp lệ. Nhiều câu trả lời không có `[id]` ngay sau từng ý (q16–q20), dù citation vẫn đúng.
    6. Corpus chỉ là bản gốc năm 2019, chưa có các sửa đổi và văn bản hướng dẫn, nên chưa dùng được cho tư vấn thực tế.
  - **Hướng tiếp theo** (cần thử trên dev, không chỉnh theo test):
    - Bước tự kiểm tra phép tính và chủ thể của Điều được trích trước khi gọi `answer`; nhắm vào q18 và q25.
    - Rerank để phân biệt các Điều có nội dung gần giống nhau, như Điều 35 và Điều 36.
    - Thử model mạnh hơn như một cấu hình riêng trên dev.

## Thử thách nâng cao (nếu thực hiện)

Không thực hiện.

## Hỗ trợ của AI và trách nhiệm
