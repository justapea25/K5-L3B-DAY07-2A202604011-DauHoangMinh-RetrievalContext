# Bài làm Day 7 — Agentic RAG trên Bộ luật Lao động 2019

Agent dùng **gpt-4o-mini** (OpenAI tool calling) để tra cứu Bộ luật Lao động 2019 (45/2019/QH14). Agent tự quyết định tìm gì và tìm bao nhiêu lần. Câu trả lời phải trích dẫn từng đoạn luật đã dùng; nếu tài liệu không đủ bằng chứng thì agent từ chối. Kho tài liệu, embedding và vector store dùng lại nguyên của Day 6.

Bài làm có ba phương pháp retrieval (dense trên pgvector Day 6, BM25, hybrid RRF), sáu cấu hình agent so sánh trên dev, và một lần đánh giá trên test sau khi đã chốt cấu hình.

## 1. Môi trường đã dùng

| Thành phần | Phiên bản / cấu hình |
|---|---|
| Máy | macOS 14.5, Apple Silicon; embedding chạy trên CPU |
| Python | 3.12.16, conda env `vinai` |
| Thư viện chính | psycopg 3.3.8, pgvector 0.4.2, sentence-transformers 5.7.0, torch 2.15.0, transformers 5.23.0, numpy 2.5.4, openai 3.51.0 (xem [requirements.txt](../requirements.txt)) |
| Vector store | PostgreSQL 16 + pgvector 0.8.7, image `pgvector/pgvector:0.8.7-pg16`, cổng `127.0.0.1:55433`; bảng `chunks`, `strategy = 'B'` của Day 6 |
| Embedding | `intfloat/multilingual-e5-small`, 384 chiều, chuẩn hóa L2, tiền tố `query: ` / `passage: `, cosine exact (không dùng ANN) |
| LLM | `gpt-4o-mini` (bản trả về: `gpt-4o-mini-2024-07-18`), temperature 0 |
| Chi phí | Tổng toàn bộ thí nghiệm dev + test: **≈ 0,108 USD**. Giá dùng để tính: 0,15 USD / 1M token input, 0,60 USD / 1M token output, ghi trong `src/agent.py` (`PRICES`); cần đối chiếu với bảng giá OpenAI hiện hành. Retrieval và embedding chạy local, không tốn phí. |

**Tương thích embedding:** khi khởi tạo, `DenseRetriever` dừng với lỗi nếu số dòng, tên model hoặc số chiều trong pgvector khác với corpus/model đang dùng. Ngoài ra đã kiểm tra thủ công: tính lại vector của một chunk và so với vector đã lưu ở Day 6, cosine = 1,0000.

## 2. Cài đặt

Cần repo Day 6 nằm cùng thư mục cha: `../K5-L3-Day06-DataIngestionEngineering`. Repo này chứa database đã index và các file `chunks_B.jsonl`, `pages.jsonl`, `benchmark/questions.jsonl`.

```bash
# 1) Python env (một lần)
conda create -n vinai python=3.12 -y
conda activate vinai
pip install -r requirements.txt

# 2) Vector store Day 6 (cần Docker Desktop đang chạy)
cd ../K5-L3-Day06-DataIngestionEngineering/starter
docker compose -p day6_student_starter up -d --wait
# Lần đầu trên máy mới, index lại theo README Day 6: python -m src.prepare && python -m src.index
cd -

# 3) Biến môi trường
cp .env.example .env      # điền OPENAI_API_KEY; DATABASE_URL mặc định trỏ tới DB Day 6
```

`.env` nằm trong `.gitignore` và không được nộp. Lần chạy đầu sẽ tải model e5-small (khoảng 470 MB) từ Hugging Face.

## 3. Chạy

Mọi lệnh chạy từ thư mục gốc repo, trong env `vinai`.

| Bước | Lệnh | Kết quả |
|---|---|---|
| Test code (offline, mock) | `python -m unittest discover -s tests -v` | 25 test: 15 của starter + 10 cho code Day 7 |
| 1. Dữ liệu + benchmark | `python -m src.prepare_data` | `data/day7/chunks.json` (252 chunk), `benchmark/questions.json`, `benchmark/cases.json` |
| 2. Benchmark retrieval | `python -m src.eval_retrieval --split dev` | `results/retrieval/dev/summary.json` + trace từng cấu hình |
| 3. Agent trên dev | `python -m src.run_agent --split dev` | `results/agent/dev/<config>/traces.json`, `summary_auto.json` |
| 4. Bảng so sánh | `python -m src.tables --split dev` | Bảng Markdown in ra màn hình |
| 5. Test (một lần, sau khi chốt) | `python -m src.eval_retrieval --split test` rồi `python -m src.run_agent --split test --only agent_dense_single agent_hybrid_multi_budget_alias` | `results/*/test/...`, kèm `reviews.json` (nháp nhãn để chấm tay) |
| 6. Phiếu chấm tay | `python -m src.review_sheet --split test --config agent_dense_single agent_hybrid_multi_budget_alias` | `review_sheet.md` cạnh trace |
| 7. Tổng hợp nhãn | `python -m src.grade --split test --config agent_dense_single agent_hybrid_multi_budget_alias` | `summary_human.json`, dùng `starter/agent_metrics.py` |

Các tham số hữu ích:
- `--only <config...>`: chỉ chạy một số cấu hình.
- `--ids q01 q24`: chỉ chạy một số câu, để debug. Nếu dùng để thử thì xóa thư mục kết quả trước khi chạy đủ, vì `reviews.json` không bị ghi đè.

Thời gian tham khảo:
- Retrieval: khoảng 20 ms/truy vấn với dense và hybrid, khoảng 1 ms với BM25.
- Agent: khoảng 2,4–3 s/câu (trung vị). Một cấu hình trên dev (22 câu) mất khoảng 1,5 phút.

## 4. Cấu trúc

```text
benchmark/
  extra_questions.json   # 10 câu viết thêm ở Day 7 (q21–q26, u01–u04)
  questions.json         # 30 câu đã hợp nhất + evidence đã kiểm chứng (sinh tự động)
  cases.json             # id/split/answerable cho agent_metrics
  README.md              # schema, định nghĩa hit, tiêu chí chọn cấu hình đã chốt
configs/
  retrieval.json         # 7 cấu hình retrieval (không LLM)
  agent.json             # 6 cấu hình agent + giả thuyết của từng cấu hình
data/day7/chunks.json    # corpus = chunk strategy B của Day 6, schema Day 7
src/
  common.py              # đường dẫn, .env, chuẩn hóa text, so khớp evidence
  prepare_data.py        # Day 6 → corpus + benchmark Day 7, kiểm chứng evidence theo trang
  retrievers.py          # DenseRetriever, BM25Retriever, HybridRetriever (RRF)
  eval_retrieval.py      # Hit@1, Evidence Hit@3, Full Hit@3, MRR@10, Context Evidence Rate
  agent.py               # vòng lặp agent, tool, context có budget, citation, điều kiện dừng
  run_agent.py           # chạy agent theo cấu hình, ghi trace + chỉ số tự động
  review_sheet.py        # phiếu chấm tay (kèm nguyên văn đoạn được trích)
  grade.py               # gộp nhãn chấm tay → starter/agent_metrics.py
  tables.py              # bảng so sánh Markdown
results/
  retrieval/{dev,test}/  # summary + trace top-k (id, score, rank, trang, chương, hit)
  agent/dev_round1/      # vòng 1: kết quả dùng để phân tích lỗi (trước khi sửa)
  agent/dev/             # vòng 2: 6 cấu hình trên cùng code
  agent/dev_connection_errors/  # lần chạy bị APIConnectionError (giữ làm bằng chứng)
  agent/test/            # baseline + cấu hình đã chọn
tests/test_day7.py       # test offline cho evidence, BM25, RRF, context, vòng lặp agent
```

## 5. Dữ liệu và benchmark

- **Corpus:** 252 chunk "mỗi Điều một chunk" (strategy B Day 6, tối đa 1.500 ký tự; Điều dài được tách theo khoản và lặp lại tiêu đề Điều). Metadata gồm `pages` (mọi trang chunk chạm tới), `chapter`, `articles`, `content_hash`.
- **Nguồn và quyền sử dụng:** văn bản quy phạm pháp luật, không thuộc đối tượng bảo hộ quyền tác giả (khoản 1 Điều 15 Luật SHTT). Chi tiết nguồn PDF ở báo cáo Day 6.
- **Benchmark:** 30 câu.

  | Split | Có đáp án | Thiếu evidence |
  |---|---:|---:|
  | dev | 20 (2 multi-hop) | 2 |
  | test | 6 (1 multi-hop) | 2 |

  - q01–q20 lấy từ Day 6. Test Day 6 không được dùng để chỉnh hệ thống.
  - 10 câu mới viết trước mọi thí nghiệm Day 7.
  - Câu multi-hop dùng `gold_groups`: mọi nhóm evidence đều bắt buộc.
  - Câu thiếu evidence có `absence_reason`, ghi cách đã kiểm tra trên toàn văn bản.
  - Chi tiết schema và định nghĩa hit: [benchmark/README.md](../benchmark/README.md).
- `prepare_data` dừng với lỗi nếu một evidence không nằm trọn trong một chunk của đúng Điều và trang. Gold không bao giờ được đưa vào retriever hay agent.

## 6. Retrieval

| Phương pháp | Cách làm |
|---|---|
| **Dense** | Embedding e5-small của query, truy vấn pgvector Day 6 (cosine exact, `ORDER BY embedding <=> q`) |
| **BM25** | Okapi BM25 (k1 = 1,5; b = 0,75) viết bằng Python thuần. Tách từ theo âm tiết; biến thể *bigram* thêm cặp âm tiết liền kề (`thử_việc`) để xấp xỉ từ ghép tiếng Việt |
| **Hybrid** | Reciprocal Rank Fusion của dense và BM25-bigram (lấy top-20 mỗi bên, k = 60, trọng số 1:1). Dùng thứ hạng nên không phải cộng hai thang score khác nhau |

- **Filter:** chỉ hỗ trợ `chapter`, lấy từ trường `filter` mà người hỏi nêu trong câu (q12–q14, q20). Filter được áp cho mọi phương pháp, và có thêm cấu hình `dense_k3_nofilter` để so sánh. Filter không bao giờ suy ra từ gold.
- **Thông tin trả về:** mỗi kết quả có `id`, `text`, `source_id`, `page`, `metadata.pages`, `chapter`, `score`, `rank`, `method`. Hybrid có thêm `component_ranks` (thứ hạng bên dense và bên BM25).
- **Xử lý lỗi:** filter không hợp lệ thì báo lỗi; DB lệch với corpus thì báo lỗi. Lỗi truy xuất trong lúc agent chạy được ghi vào trace và báo cho model, không thay bằng kết quả giả.

## 7. Agent và context

- **Tool:**
  - `search_law(query)`: dùng phương pháp retrieval theo cấu hình.
  - `answer(answer, citations[])`: câu trả lời cuối kèm trích dẫn.
  - `abstain(reason)`: từ chối khi không đủ bằng chứng.

  Model bắt buộc gọi tool (`tool_choice = required`), mỗi lượt một tool.
- **Context:** gộp chunk của mọi lượt tìm và bỏ trùng, giới hạn theo `budget_chars`. Có hai cách chọn khi vượt budget:
  - `first_come`: chunk vào trước được giữ, giống starter.
  - `best_rank`: ưu tiên chunk hạng 1 của mọi lượt tìm, rồi đến hạng 2, hạng 3.
- **Citation:** có hai chế độ.
  - `id`: model trích nguyên chunk ID.
  - `alias`: mỗi đoạn có nhãn ngắn `[S1]`, `[S2]`; model trích nhãn và code ánh xạ lại về chunk ID trong kết quả.

  Citation không có trong context cuối thì câu trả lời bị từ chối, cho sửa một lần, sau đó chuyển thành abstain.
- **Điều kiện dừng:**
  - Model gọi `answer` hoặc `abstain`.
  - Đạt `max_searches`: tool tìm kiếm bị gỡ, model buộc phải trả lời hoặc từ chối.
  - Đạt `max_steps = 8` lượt gọi model: chuyển thành abstain.
- **Bảo vệ:** system prompt quy định nội dung tài liệu là dữ liệu, không phải chỉ dẫn.
- **Trace mỗi câu:** từng tool call (tham số, query, top-k kèm score, context sau mỗi lượt), context cuối, câu trả lời, citation, lý do dừng, số lượt tìm, token, chi phí, thời gian và lỗi.

## 8. Cấu hình đã thử và lựa chọn

Retrieval (dev): 7 cấu hình trong [configs/retrieval.json](../configs/retrieval.json), gồm dense, BM25 unigram, BM25 bigram, hybrid, các biến thể top-k 3/5 và có/không filter.

Agent (dev): 6 cấu hình trong [configs/agent.json](../configs/agent.json), mỗi cấu hình ghi kèm giả thuyết:

| Cấu hình | Thay đổi so với cấu hình trước |
|---|---|
| `agent_dense_single` | **Baseline**: dense top-3, 1 lượt tìm, budget 4000, `first_come` |
| `agent_dense_multi` | Cho tìm tối đa 4 lượt |
| `agent_hybrid_multi` | Đổi sang hybrid |
| `agent_hybrid_multi_budget` | Budget 8000 + `best_rank` (sửa lỗi q11/q21/q25: evidence bị loại vì budget) |
| `agent_hybrid_multi_budget_alias` | Citation `[S#]` (sửa lỗi q12/q15/q21: trả lời đúng nhưng bịa chunk ID theo số khoản) |
| `agent_dense_multi_budget_alias` | Đối chứng: như trên nhưng dùng dense thay hybrid |

Tiêu chí chọn và quyết định được ghi trong [benchmark/README.md](../benchmark/README.md) trước khi chạy test. **Cấu hình chọn: `agent_hybrid_multi_budget_alias`**. Bảng kết quả, nhãn chấm tay, phân tích lỗi và giới hạn nằm trong báo cáo cá nhân [report/individual/](../report/individual/).


