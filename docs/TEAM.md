# Danh Sách Thành Viên & Báo Cáo Phân Công Nhóm

- **Tên Nhóm:** `DataGuard-AI`
- **Mã Nhóm / Lớp:** `K4-L3-DAY10`
- **Tên Repository Nộp Bài:** `K4-L3A-Day10-Data-Pipeline-Data-Observability`
- **Link Repository:** `https://github.com/chinhzz108/K4-L3A-Day10-Data-Pipeline-Data-Observability`

---

## 1. Thành viên

| STT | Họ và tên | MSSV | Email / GitHub | Vai trò & Phân công công việc | Báo cáo cá nhân |
|---:|---|---|---|---|---|
| 1 | Trần Trọng Chinh | 2A202602720 | chinhzz108 (chinhzz108@gmail.com) | Toàn quyền phụ trách toàn bộ hệ thống Data Pipeline & Observability | `report/2A202602720_TranTrongChinh.md` |

---

## 2. Phần Tự Khai Báo Đóng Góp Chi Tiết Cá Nhân

### Trần Trọng Chinh - 2A202602720 (GitHub: chinhzz108)
- **Vai trò:** Thực hiện độc lập toàn bộ hệ thống (Solo Developer & Pipeline Architect).
- **Công việc chi tiết đã hoàn thành:**
  - **Môi trường & Cấu hình:** Thiết lập môi trường ảo chuẩn hóa qua `uv`, quản lý cấu hình tập trung trong `src/core/config.py` và các tiện ích `src/core/utils.py`.
  - **Ingestion & Data Lineage (`src/ingestion/crossref.py`):** Xây dựng module thu thập Crossref Academic REST API, bóc tách metadata, làm sạch thẻ XML/JATS, lưu trữ an toàn 2 file thô `crossref_response.json` và `crossref_records.json` với cơ chế cứu hộ offline khi mất mạng hoặc dính HTTP 429.
  - **Data Cleaning & Enrichment (`src/ingestion/cleaning.py`):** Chuẩn hóa schema, tính toán trường `age_days`, xây dựng đoạn text nhúng 5 phần `text_for_embedding`, và khử trùng lặp theo `paper_id`.
  - **Data Observability Gate (`src/observability/quality.py`):** Thiết lập chốt kiểm dịch Great Expectations 1.x (ephemeral context) với 4 Expectations cốt lõi (row count, non-null, unique DOI, summary length) và cơ chế giám sát Freshness SLA (ngưỡng 180 ngày).
  - **RAG & Vector Database (`src/retrieval/`):** Tích hợp mô hình `sentence-transformers/all-MiniLM-L6-v2`, quản lý độc lập 3 collections trong ChromaDB (`papers-baseline`, `papers-corrupted`, `papers-repaired`), xây dựng QA Agent trích xuất câu trả lời chuẩn xác.
  - **Benchmark Evaluation (`src/evaluation/`):** Xây dựng bộ đề thi chuẩn 10 câu hỏi qua 4 nghiệp vụ (`summary`, `authors`, `date`, `categories`), đo lường Hit Rate, Token F1 và LLM Judge.
  - **Synthetic Corruption & Idempotent Repair (`src/ingestion/corruption.py`, `src/pipelines/`):** Thiết kế 6 kịch bản tiêm lỗi dữ liệu thực tế, chứng minh hiện tượng Silent Failure (Hit Rate giảm từ 100% về 60%), và xây dựng cơ chế phục hồi tự động Idempotent khôi phục 100% phong độ từ raw lineage.
  - **Bonus Features:** Xây dựng Dashboard trực quan HTML `data/quality/observability_dashboard.html`, thiết lập bộ automated tests Pytest (8/8 tests pass) và GitHub Actions CI workflow.
- **Điều học được / Đóng góp chính:**
  - Nắm vững bản chất nguy hiểm của Silent Failure trong hệ thống AI Production.
  - Thành thạo Great Expectations 1.x và kiến trúc Data Observability để giám sát chất lượng dữ liệu liên tục.
  - Làm chủ nguyên lý Idempotent Pipeline — nền tảng sống còn của kỹ thuật MLOps hiện đại.
