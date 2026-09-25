# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Khóa/Lớp         | K4 - L3A - Day 10          |
| Tên nhóm         | DataGuard-AI               |
| Repository         | https://github.com/chinhzz108/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26                 |

### Thành viên và phân công

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Trần Trọng Chinh | 2A202602720 | Solo Developer & Pipeline Architect | Toàn bộ codebase: `core/`, `ingestion/`, `retrieval/`, `observability/`, `evaluation/`, `pipelines/` |

---

## 2. Tóm tắt kết quả

Nhóm DataGuard-AI đã hoàn thành 100% các yêu cầu từ CP0 đến CP6 cùng các hạng mục điểm thưởng (Pytest CI suite và Observability Dashboard).

1. **Baseline Pipeline:** Thu thập và chuẩn hóa 24 bản ghi nghiên cứu từ Crossref Academic API, lưu trữ an toàn hai file thô `crossref_response.json` và `crossref_records.json`. Trạm kiểm soát chất lượng Great Expectations 1.x xác thực 100% hợp lệ, Freshness SLA đạt chuẩn (chỉ 4.2% tài liệu quá hạn). Mô hình embedding `all-MiniLM-L6-v2` nạp vào ChromaDB giúp QA Agent đạt **100.0% Retrieval Hit Rate** và **1.0000 Mean Token F1**.
2. **Controlled Corruption:** Tiêm 6 kịch bản lỗi thực tế (drop 20% bản ghi mới, xóa trắng tóm tắt, chèn chuỗi ký tự rác, cắt ngắn tiêu đề, lùi ngày xuất bản 365 ngày, nhân bản dòng). Hiện tượng **Silent Failure** lập tức xuất hiện: Agent không báo lỗi hệ thống nhưng Retrieval Hit Rate sụt giảm nghiêm trọng từ **100% xuống 60.0%**, Token F1 giảm xuống **0.8506**. Tuy nhiên, Data Quality Gate (GX 1.x) và Freshness SLA lập tức phát hiện và gióng chuông cảnh báo vi phạm.
3. **Idempotent Repair:** Tự động tái tạo toàn bộ dữ liệu từ bản lưu thô ban đầu mà không cần sửa tay. Kết quả sau phục hồi lấy lại chính xác **100.0% Retrieval Hit Rate** và **1.0000 Token F1**, chứng minh năng lực tự chữa lành hoàn toàn (Self-Healing).

---

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Nguồn Crossref REST API (hoặc Snapshot Local data/raw/)
    ├── 1. Ingestion & Raw Preservation -> data/raw/crossref_records.json
    ├── 2. Transformation & Enrichment   -> data/clean/papers_clean.csv (age_days, text_for_embedding)
    ├── 3. Data Observability Gate       -> Great Expectations 1.x & Freshness SLA Check
    ├── 4. Vector Embedding & Indexing   -> sentence-transformers + ChromaDB (papers-baseline)
    ├── 5. Evaluation Benchmark          -> 10-Question Test Set (Hit Rate, Token F1, LLM Judge)
    ├── 6. Synthetic Corruption Suite    -> 6 dạng lỗi thực tế -> data/clean/papers_clean_corrupted.csv
    └── 7. Idempotent Repair & Compare   -> Rebuild từ Raw Snapshot -> data/reports/corruption_report.md
```

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref API / JSON snapshot | Fetch, retry logic, bóc tách abstract bỏ thẻ XML/JATS, parse PaperRecord | `data/raw/crossref_response.json`, `data/raw/crossref_records.json` | Trần Trọng Chinh |
| Cleaning | Raw `PaperRecord` objects | Chuẩn hóa chuỗi, tính `age_days`, tạo `text_for_embedding`, khử trùng lặp theo `paper_id` | `data/clean/papers_clean.csv`, `data/clean/papers_clean.json` | Trần Trọng Chinh |
| Embedding & Index | Cleaned DataFrame | Nhúng vector `all-MiniLM-L6-v2`, quản lý collection ChromaDB độc lập | `data/chroma/`, `data/embeddings/` | Trần Trọng Chinh |
| Evaluation | Cleaned DataFrame, Chroma Index | Sinh 10 câu hỏi chuẩn hóa qua 4 nhóm nghiệp vụ, đo Hit Rate, Token F1, LLM Judge | `data/eval/test_set.json`, `data/results/*_metrics.json` | Trần Trọng Chinh |
| Observability | Cleaned / Corrupted DataFrame | Ephemeral GX 1.x Context với 4 Expectations thiết yếu, giám sát Freshness SLA | `data/quality/*_quality_report.json`, `freshness_report.json` | Trần Trọng Chinh |
| Corruption & Repair | Clean DataFrame / Raw Snapshot | Tiêm 6 dạng độc tố dữ liệu; kích hoạt quy trình tự phục hồi Idempotent | `corruption_log.json`, `data/reports/corruption_report.md` | Trần Trọng Chinh |
| Orchestration | CLI Scripts | Điều phối toàn tuyến Phase 1 và Phase 2, xuất Markdown report và Dashboard | `script/run_phase1.py`, `script/run_corruption_flow.py` | Trần Trọng Chinh |

---

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `gemini` (hỗ trợ fallback tự động sang Heuristic / Mock) |
| `LLM_MODEL` | `gemini-2.5-flash` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Số lượng Crossref records | 24 |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày (SLA vi phạm nếu stale > 25%) |

### Lệnh cài đặt

```bash
uv sync
```
Hoặc với `pip`:
```bash
python -m pip install -e .
```

### Lệnh chạy thực nghiệm

```bash
# 1. Chạy Pha 1 - Baseline Pipeline
python script/run_phase1.py

# 2. Chạy Pha 2 - Tiêm lỗi dữ liệu, đo suy giảm & phục hồi Idempotent
python script/run_corruption_flow.py

# 3. Chạy kiểm thử tự động toàn diện (Pytest CI)
pytest -v tests/test_pipeline.py

# 4. Sinh Dashboard trực quan HTML
python src/observability/dashboard.py
```

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | Thành công (Exit 0) | 2026-09-26 00:14:25 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | Thành công (Exit 0) | 2026-09-26 00:17:31 | `data/results/corrupted_metrics.json`, `data/reports/corruption_report.md` |
| Pytest Test Suite | 8/8 Tests Passed | 2026-09-26 00:18:41 | `tests/test_pipeline.py` (Coverage > 85%) |

---

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API (`https://api.crossref.org/works`) |
| Query/filter | `query=agentic retrieval augmented generation large language model`, `filter=has-abstract:true` |
| Thời điểm lấy dữ liệu | Snapshot offline chuẩn kèm cơ chế Live Fetch tự động fallback |
| Số record nhận được | 24 records |
| Cơ chế retry/backoff | Timeout 15s, tự động chuyển đổi đọc file snapshot khi gặp HTTP 429 hoặc mất mạng |

### Raw và clean schema

| Trường | Kiểu dữ liệu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | `str` | Có | Mã định danh DOI duy nhất | Bỏ qua record nếu thiếu DOI |
| `title` | `str` | Có | Tiêu đề bài báo khoa học | Bỏ qua record nếu thiếu tiêu đề |
| `summary` | `str` | Có | Tóm tắt nội dung bài báo | Loại bỏ thẻ XML/JATS `<jats:p>`, chuẩn hóa khoảng trắng |
| `authors` | `list[str]` | Có | Danh sách tác giả | Ghép họ tên hoặc gán "Unknown Author" |
| `categories` | `list[str]` | Có | Lĩnh vực chuyên môn | Lấy trường subject hoặc gán "General" |
| `published` | `str` | Có | Ngày xuất bản ISO (YYYY-MM-DD) | Parse từ date-parts hoặc lấy ngày hiện tại |
| `age_days` | `int` | Có | Tuổi của bài báo tính theo ngày | `(run_date - published).days`, chặn dưới >= 0 |
| `text_for_embedding` | `str` | Có | Đoạn văn bản hoàn chỉnh 5 phần để vector hóa | Tự động ghép format Title + Authors + Published + Categories + Summary |

---

## 6. Evaluation Setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | 10 câu hỏi cố định |
| Các `question_type` | `summary` (3 câu), `authors` (3 câu), `date` (2 câu), `categories` (2 câu) |
| Ground-truth document ID | DOI tương ứng của bài báo trong corpus |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store / collections | ChromaDB: `papers-baseline`, `papers-corrupted`, `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | `gemini-2.5-flash` (kèm fallback Heuristic Token-F1 Judge) |
| Test set dùng chung | `data/eval/test_set.json` |

*Giải thích:* Test set được cố định bất biến giữa 3 pha đánh giá (Baseline, Corrupted, Repaired) nhằm tuân thủ nguyên tắc đo lường khoa học: **giữ nguyên đề thi để so sánh công bằng năng lực của hệ thống trước và sau khi bị tác động**.

---

## 7. Kết quả Baseline

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | **100.0%** | 10/10 câu hỏi truy xuất chính xác tài liệu chứa câu trả lời |
| `mean_token_f1` | **1.0000** | Câu trả lời trích xuất trùng khớp tuyệt đối với ground-truth |
| `judge_accuracy` | **100.0%** | Giám khảo LLM đánh giá câu trả lời chính xác về mặt ngữ nghĩa |
| `mean_judge_score` | **5.00 / 5.0** | Điểm số chất lượng tối đa |

---

## 8. Data Quality và Freshness

### Great Expectations 1.x Quality Checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `ExpectTableRowCountToBeBetween` | Completeness | [5, 5000] dòng | **PASSED** (24 dòng) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull(paper_id)` | Completeness | 0% null | **PASSED** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull(title)` | Completeness | 0% null | **PASSED** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToNotBeNull(text_for_embedding)` | Completeness | 0% null | **PASSED** (0 null) | `baseline_quality_report.json` |
| `ExpectColumnValuesToBeUnique(paper_id)` | Uniqueness | 100% unique | **PASSED** (0 duplicate) | `baseline_quality_report.json` |
| `ExpectColumnValueLengthsToBeBetween(summary)` | Validity | >= 30 ký tự | **PASSED** (Độ dài chuẩn) | `baseline_quality_report.json` |

### Freshness SLA

- **Ngưỡng SLA:** `age_days > 180` ngày không được vượt quá 25% tổng số tài liệu.
- **Kết quả Baseline:** 1 / 24 bài báo quá hạn (4.2%) $\rightarrow$ **PASSED (Fresh)**.
- **Kết quả Corrupted:** 8 / 22 bài báo quá hạn (36.4%) $\rightarrow$ **FAILED (SLA Breach Detected)**.

---

## 9. Corruption Scenarios và Repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| `drop_latest_records` | Cắt bỏ 20% bản ghi mới nhất | 4 bài báo | Thiếu tài liệu gần đây | Retrieval Hit Rate sụt giảm từ 100% xuống 60% | Tái tạo toàn bộ từ `crossref_records.json` |
| `blank_summary` | Xóa rỗng trường summary | 2 bài báo | `ExpectColumnValueLengthsToBeBetween` FAILED | Bóp méo ngữ cảnh nhúng vector | Nạp lại dữ liệu gốc từ snapshot |
| `inject_noise` | Thêm chuỗi ký tự rác | 2 bài báo | Gây nhiễu vector ngữ nghĩa | Giảm Token F1 của câu trả lời | Loại bỏ nhiễu bằng transform pipeline |
| `truncate_title` | Cắt ngắn tiêu đề < 8 ký tự | 2 bài báo | Sai lệch tiêu đề | Exact lookup thất bại | Re-extract title từ raw JSON |
| `stale_date` | Lùi ngày xuất bản 365 ngày | 8 bài báo | Freshness SLA FAILED (36.4%) | Cảnh báo hệ thống dữ liệu bị mốc | Tính lại `age_days` chuẩn từ raw |
| `duplicate_rows` | Nhân bản 2 dòng có sẵn | 2 bài báo | `ExpectColumnValuesToBeUnique` FAILED | Làm loãng không gian vector | Khử trùng lặp theo `subset=['paper_id']` |

---

## 10. So sánh Baseline vs Corrupted vs Repaired

| Metric / Signal | Baseline (Clean) | Corrupted (Silent Failure) | Repaired (Self-Healing) | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | **100.0%** | **60.0%** | **100.0%** | -40.0% | **+40.0%** | Sụt giảm nghiêm trọng khi mất dữ liệu, phục hồi 100% |
| `mean_token_f1` | **1.0000** | **0.8506** | **1.0000** | -0.1494 | **+0.1494** | Câu trả lời bị sai lệch/nhiễu, phục hồi hoàn hảo |
| `judge_accuracy` | **100.0%** | **90.0%** | **100.0%** | -10.0% | **+10.0%** | Giám khảo phát hiện câu trả lời suy giảm |
| `mean_judge_score` | **5.00** | **4.20** | **5.00** | -0.80 | **+0.80** | Điểm số trung bình suy giảm rõ rệt |
| Quality checks (GX) | **PASSED** | **FAILED** | **PASSED** | Báo động đỏ | **Khôi phục** | GX 1.x chặn đứng bản ghi rỗng & trùng lặp |
| Freshness SLA | **PASSED** | **FAILED** | **PASSED** | Cảnh báo quá hạn | **Khôi phục** | Tỷ lệ stale giảm từ 36.4% về lại 4.2% |

### Hai kết luận nhân quả có bằng chứng:
1. **Dữ liệu bẩn sinh ra Silent Failure:** Việc xóa tóm tắt và bỏ rơi bản ghi mới khiến Vector Store không thể truy xuất đúng ngữ cảnh (Hit Rate giảm 40%), nhưng hệ sinh thái RAG không ném Exception nào — Agent vẫn trả lời tự tin nhưng nội dung bị sai sự thật.
2. **Tính Idempotent giúp phục hồi hoàn toàn:** Nhờ kiến trúc Data Lineage lưu trữ bản thô nguyên bản (`crossref_records.json`), khi kích hoạt hàm Repair, pipeline thực hiện transform xác định (deterministic) đưa mọi chỉ số về mức ban đầu mà không cần can thiệp thủ công.

---

## 11. Vấn đề tích hợp quan trọng

- **Triệu chứng:** Khi chạy LLM Judge với Google Gemini Free Tier, sau 5 câu hỏi hệ thống gặp lỗi `429 RESOURCE_EXHAUSTED` do chạm giới hạn 5 Requests/Phút (RPM) và 20 Requests/Ngày.
- **Nguyên nhân:** LangChain Google GenAI mặc định có cơ chế retry nhiều lần với thời gian chờ exponential backoff lên đến 45 giây/lần thử, gây hiện tượng pipeline bị treo lâu.
- **Cách xử lý:** 
  1. Thêm tham số `max_retries=1` trong cấu hình `ChatGoogleGenerativeAI` tại `src/retrieval/llm.py`.
  2. Bổ sung fallback heuristic judge tự động trong `src/evaluation/metrics.py` để tính điểm dựa trên Token F1 khi LLM API chạm giới hạn hạn ngạch.
- **Cách xác minh:** Pipeline chạy trơn tru end-to-end trong vòng chưa đầy 30 giây mà vẫn đảm bảo tính chính xác 100% của chỉ số đánh giá.

---

## 12. Checklist trước khi nộp bài

- [x] Đã chạy thành công `python script/run_phase1.py` (Exit code 0).
- [x] Đã chạy thành công `python script/run_corruption_flow.py` (Exit code 0).
- [x] Đã chạy thành công `pytest -v tests/test_pipeline.py` (8/8 tests pass).
- [x] Đã tạo Dashboard trực quan `data/quality/observability_dashboard.html`.
- [x] Báo cáo đối chiếu 3 trạng thái đầy đủ số liệu tại `data/reports/corruption_report.md`.
- [x] Không commit API Key / `.env` lên GitHub (đã nằm trong `.gitignore`).
- [x] File `docs/TEAM.md` và các báo cáo cá nhân đã được điền đầy đủ.
