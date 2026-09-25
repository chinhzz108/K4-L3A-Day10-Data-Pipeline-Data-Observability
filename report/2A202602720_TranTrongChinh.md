# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin         | Nội dung                  |
| ------------------ | -------------------------- |
| Họ và tên       | Trần Trọng Chinh           |
| MSSV               | 2A202602720                |
| Khóa/Lớp         | K4 - L3A - Day 10          |
| Tên nhóm         | DataGuard-AI               |
| Vai trò chính    | Solo Developer & Pipeline Architect |
| Repository         | https://github.com/chinhzz108/K4-L3A-Day10-Data-Pipeline-Data-Observability |
| Ngày hoàn thành | 2026-09-26                 |

---

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | --------------------- | ---------------- | ----------------- | -------------------------------------------- |
| Ingestion & Lineage | `src/ingestion/crossref.py` | Crossref REST API / Snapshot | Raw response & parsed records JSON | Hoàn thành |
| Data Cleaning & Modeling | `src/ingestion/cleaning.py` | Raw `PaperRecord` objects | `papers_clean.csv`, `papers_clean.json` | Hoàn thành |
| Observability Gate & SLA | `src/observability/quality.py` | Clean & Corrupted DataFrame | Great Expectations 1.x & Freshness reports | Hoàn thành |
| RAG Vector Index & Retrieval | `src/retrieval/index.py`, `embeddings.py`, `qa.py` | Cleaned DataFrame | Chroma collections (`papers-baseline`, etc.) | Hoàn thành |
| Benchmark Evaluation | `src/evaluation/testset.py`, `metrics.py` | Chroma Index, DataFrame | `test_set.json`, baseline/corrupted metrics | Hoàn thành |
| Data Corruption Suite | `src/ingestion/corruption.py` | Clean DataFrame | 6 corruptions, `corruption_log.json` | Hoàn thành |
| Pipeline Orchestration | `src/pipelines/phase1.py`, `corruption_flow.py` | Toàn bộ modules | Phase 1 & 3-state comparison reports | Hoàn thành |
| Observability Dashboard (Bonus B1) | `src/observability/dashboard.py` | Quality reports, metrics JSON | `observability_dashboard.html` | Hoàn thành |
| Automated Pytest CI Suite (Bonus B3) | `tests/test_pipeline.py`, `.github/workflows/ci.yml` | Pipeline modules | 8/8 Tests Passed, GitHub Actions | Hoàn thành |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------------- | ----------------------------- | ------------------------- | ----------------------- |
| Xây dựng Ingestion với Fallback | `src/ingestion/crossref.py` | Tải và bóc tách chuẩn 24 bài báo khoa học | `python script/run_phase1.py` |
| Làm sạch và chuẩn hóa schema | `src/ingestion/cleaning.py` | Cột `text_for_embedding` 5 phần, `age_days` | `papers_clean.csv` (24 dòng) |
| Thiết lập chốt kiểm dịch GX 1.x | `src/observability/quality.py` | Ephemeral GX 1.x Suite (4 expectations), Freshness SLA | `baseline_quality_report.json` |
| Xây dựng Vector Index ChromaDB | `src/retrieval/index.py` | 3 collection ChromaDB độc lập, mô hình MiniLM | `data/chroma/` |
| Xây dựng Baseline & Corruption Flow | `src/pipelines/` | Báo cáo đối chiếu 3 trạng thái chứng minh phục hồi 100% | `script/run_corruption_flow.py` |
| Triển khai Test Suite tự động | `tests/test_pipeline.py` | 8/8 unit tests pass hoàn hảo | `pytest -v tests/test_pipeline.py` |
| Xây dựng Observability Dashboard | `src/observability/dashboard.py` | Web dashboard hiển thị chart SLA và so sánh 3 trạng thái | `python src/observability/dashboard.py` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Hệ thống RAG thông thường dễ mắc lỗi **Silent Failure**: khi dữ liệu đầu vào bị lỗi hoặc lỗi thời, AI vẫn trả lời trôi chảy nhưng nội dung là thông tin sai lệch (Hallucination) mà không báo lỗi runtime. Tôi đã độc lập thiết kế và triển khai toàn diện luồng dữ liệu, tích hợp "chốt kiểm dịch" Great Expectations 1.x để chặn đứng dữ liệu xấu trước khi lọt vào Vector Store, đồng thời thiết kế cơ chế **Idempotent Repair** tự động khôi phục dữ liệu sạch từ bản lưu trữ thô ban đầu.

### Cách triển khai
1. **Raw Preservation & Lineage:** Mọi dữ liệu tải từ API đều được cất giữ nguyên bản tại `crossref_response.json` và `crossref_records.json` trước khi biến đổi, tạo nguồn gốc xác thực cho cơ chế tự phục hồi.
2. **Data Observability Gate (GX 1.x):** Sử dụng `gx.get_context(mode="ephemeral")` với 4 expectations (row count, non-null, unique DOI, summary length) và giám sát Freshness SLA (`age_days > 180` ngày).
3. **Synthetic Corruption:** Thiết kế 6 lỗi dữ liệu thực tế (bỏ rơi bản ghi mới, xóa tóm tắt, chèn chuỗi rác, cắt ngắn tiêu đề, làm cũ ngày tháng, nhân bản dòng). Kết quả chứng minh rõ rệt sự sụp đổ chỉ số RAG (Hit Rate giảm từ 100% xuống 60.0%).
4. **Idempotency Guarantee:** Hàm Repair tái thực thi toàn bộ logic làm sạch và nhúng vector trực tiếp từ `crossref_records.json`, đưa 100% các chỉ số về trạng thái sạch ban đầu mà không cần can thiệp thủ công.

---

## 5. Checklist nghiệm thu

- [x] Đã chạy thành công `run_phase1.py` và `run_corruption_flow.py` (Exit code 0).
- [x] Đã kiểm thử tự động với Pytest (8/8 passed).
- [x] Báo cáo cá nhân và nhóm khớp hoàn toàn với các số liệu thực nghiệm.
- [x] Mã nguồn sạch sẽ, không chứa secrets hay đường dẫn tuyệt đối local.
- [x] Đã thiết lập GitHub Actions CI và Observability Dashboard.
