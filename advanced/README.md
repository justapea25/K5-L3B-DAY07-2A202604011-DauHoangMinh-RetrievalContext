# Thử thách nâng cao — tài liệu 237 trang có bảng, ảnh, biểu đồ

## Tài liệu nguồn

|                 |                                                                                                                                                                                                                                                                                                         |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Tên            | Kết quả chủ yếu Điều tra biến động dân số và kế hoạch hóa gia đình thời điểm 01/4/2025                                                                                                                                                                                              |
| Cơ quan        | Cục Thống kê (Bộ Tài chính)                                                                                                                                                                                                                                                                       |
| Trang công bố | [https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/08/ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-va-ke-hoach-hoa-gia-dinh-thoi-diem-01-4-2025/](https://www.nso.gov.vn/du-lieu-va-so-lieu-thong-ke/2026/08/ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-va-ke-hoach-hoa-gia-dinh-thoi-diem-01-4-2025/) |
| File PDF        | [https://www.nso.gov.vn/wp-content/uploads/2026/08/Sach-ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-2025.-pdf.pdf](https://www.nso.gov.vn/wp-content/uploads/2026/08/Sach-ket-qua-chu-yeu-dieu-tra-bien-dong-dan-so-2025.-pdf.pdf)                                                                         |
| Số trang       | 237 trang PDF; số trang in = trang PDF − 1                                                                                                                                                                                                                                                            |
| SHA-256         | `d2178d7b8fb71699c67eed4c4382d10c8658ea0bca06793ae4d2abeee706c2fe`                                                                                                                                                                                                                                    |

```bash
# cần GEMINI_API_KEY trong .env (đọc biểu đồ và trang phiếu điều tra bằng vision model)
python -m advanced.fetch      # tải PDF + kiểm tra SHA-256
python -m advanced.ingest     # chunk text/bảng/biểu đồ/phiếu → playground/advanced_build/
python -m advanced.index      # dựng index dense + BM25 cho 490 chunk
python -m advanced.run --validate                                          # kiểm tra benchmark với tài liệu
python -m advanced.run --split test_v2 --only adv_hybrid_multi_v4_gpt-6-luna
```

- Benchmark: [advanced/benchmark/questions.json](benchmark/questions.json)
- Kết quả: [advanced/results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/](results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/)
  - Trace từng câu: [traces.json](results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/traces.json)
  - Nhãn và lý do: [labels.json](results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/labels.json)
  - Tổng hợp: [summary_auto.json](results/test_v2/adv_hybrid_multi_v4_gpt-6-luna/summary_auto.json)
- Kết quả theo nhóm và phân tích lỗi: [report/individual/2A202604011_DauHoangMinh.md](../report/individual/2A202604011_DauHoangMinh.md)
