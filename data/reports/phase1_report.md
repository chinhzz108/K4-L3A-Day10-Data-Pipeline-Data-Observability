# Day 10 — Baseline Phase 1 Report: Scholarly Data Pipeline & Observability

**Pipeline Execution Time:** 2026-09-25 17:14:25 UTC  
**Data Source:** Crossref Academic REST API (with Local Snapshot Fallback)  
**Corpus Domain:** Agentic Retrieval-Augmented Generation & LLM Systems  

---

## 1. Data Ingestion & Lineage

The raw metadata ingestion phase fetched and preserved authoritative scholarly records with full lineage tracking:

- **Raw API Response:** `C:\Users\Chinhdz\Downloads\K4-L3A-Day10-Data-Pipeline-Data-Observability-main\data\raw\crossref_response.json`
- **Parsed Raw Records:** `C:\Users\Chinhdz\Downloads\K4-L3A-Day10-Data-Pipeline-Data-Observability-main\data\raw\crossref_records.json`
- **Cleaned Dataset:** `C:\Users\Chinhdz\Downloads\K4-L3A-Day10-Data-Pipeline-Data-Observability-main\data\clean\papers_clean.csv`
- **Total Ingested Records:** 24
- **Cleaned & Deduplicated Rows:** 24

---

## 2. Data Observability & Quality Gates (Great Expectations 1.x)

Data quality checks were validated using ephemeral **Great Expectations 1.x** batch definitions before vector indexing:

| Expectation / Rule | Validation Result |
| :--- | :--- |
| `expect_table_row_count_to_be_between` | **PASSED** |
| `expect_column_values_to_not_be_null` | **PASSED** |
| `expect_column_values_to_be_unique` | **PASSED** |
| `expect_column_values_to_not_be_null` | **PASSED** |
| `expect_column_values_to_not_be_null` | **PASSED** |
| `expect_column_value_lengths_to_be_between` | **PASSED** |

- **Overall GX Gate Status:** **PASSED (100%)**
- **Freshness Threshold:** 180 days
- **Stale Records (> 180 days):** 1 / 24 (4.2%)
- **Freshness SLA Status:** **PASSED (Compliant)** (Threshold SLA <= 25%)

---

## 3. RAG Retrieval & Evaluation Benchmark

The baseline vector store was indexed into ChromaDB (`papers-baseline`) using `sentence-transformers/all-MiniLM-L6-v2`. Performance was evaluated against a standard 10-question ground truth test set:

| Evaluation Metric | Baseline Value | Standard Target | Status |
| :--- | :---: | :---: | :---: |
| **Total Evaluation Samples** | 10 | 10 | Complete |
| **Retrieval Hit Rate** | **100.0%** | >= 80% | Optimal |
| **Mean Token F1** | **1.0000** | >= 0.60 | High Semantic Match |
| **LLM Judge Accuracy** | **100.0%** | >= 80% | Verified |
| **LLM Judge Mean Score** | **5.00 / 5.0** | >= 3.5 | Reliable |

---

## 4. Key Takeaways & Architecture Integrity

1. **Deterministic Preprocessing:** All text cleaning (HTML/JATS tag stripping, whitespace collapse, composite embedding string generation) executed cleanly without record loss.
2. **Quality Quarantine Guarantee:** Zero null values in critical fields (`paper_id`, `title`, `text_for_embedding`) and zero duplicates were observed.
3. **Serving Layer Health:** High baseline retrieval hit rate demonstrates vector index readiness for the downstream agent.
