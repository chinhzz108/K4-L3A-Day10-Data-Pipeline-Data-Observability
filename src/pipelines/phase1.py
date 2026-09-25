from __future__ import annotations

import logging
from core.config import load_settings
from core.utils import now_utc, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from evaluation.testset import build_test_set
from ingestion.cleaning import build_clean_dataframe
from ingestion.crossref import fetch_source_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_phase1_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Execute Phase 1 Baseline Data Pipeline End-to-End:

    1. Load configuration and paths.
    2. Ingest Crossref scholarly records (with local fallback).
    3. Transform, clean, and enrich metadata (age_days, text_for_embedding).
    4. Save clean dataset to CSV and JSON.
    5. Build Chroma vector index for baseline collection.
    6. Generate benchmark evaluation test set.
    7. Execute Great Expectations 1.x Quality Gate & Freshness SLA analysis.
    8. Evaluate retrieval hit rate and token F1 against ground truth.
    9. Render Phase 1 Baseline Markdown report.
    """
    logger.info("=== Starting Phase 1: Baseline Data Pipeline ===")
    settings = load_settings()

    # Step 1: Ingestion
    logger.info("Ingesting raw Crossref records...")
    records = fetch_source_records(settings)
    logger.info(f"Loaded {len(records)} raw records.")

    # Step 2: Cleaning
    logger.info("Cleaning records and building embedding text...")
    clean_df = build_clean_dataframe(records, now_utc())
    logger.info(f"Cleaned {len(clean_df)} records.")

    # Step 3: Persist Clean Artifacts
    write_csv(clean_df, settings.paths.clean_csv)
    write_json(settings.paths.clean_json, clean_df.to_dict(orient="records"))
    logger.info(f"Saved clean dataset to {settings.paths.clean_csv} and {settings.paths.clean_json}")

    # Step 4: Quality Gate & Freshness Check
    logger.info("Running Great Expectations 1.x Quality Gate...")
    quality_res = run_data_quality_checks(clean_df, settings, "baseline")
    logger.info("Generating Freshness SLA report...")
    freshness_res = build_freshness_report(clean_df, settings, settings.paths.freshness_report)

    # Step 5: Vector Indexing
    logger.info(f"Building Chroma vector index in collection '{settings.baseline_collection_name}'...")
    index = LocalEmbeddingIndex.build(clean_df, settings, settings.paths.embeddings_json)
    logger.info("Chroma indexing complete.")

    # Step 6: Test Set Generation
    logger.info("Generating 10-question evaluation benchmark...")
    build_test_set(clean_df, settings.paths.eval_testset)
    logger.info(f"Test set saved to {settings.paths.eval_testset}")

    # Step 7: Evaluate Baseline RAG
    logger.info("Evaluating baseline retrieval and answer metrics...")
    evaluation_bundle = evaluate_pipeline(
        settings=settings,
        index=index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.baseline_metrics,
        answers_output_path=settings.paths.baseline_answers,
    )
    logger.info(f"Baseline Metrics: {evaluation_bundle.summary}")

    # Step 8: Generate Report
    logger.info("Compiling Phase 1 Baseline report...")
    source_summary = {
        "timestamp": now_utc().strftime("%Y-%m-%d %H:%M:%S UTC"),
        "raw_api_response": "data/raw/crossref_response.json",
        "raw_records_json": "data/raw/crossref_records.json",
        "clean_csv": "data/clean/papers_clean.csv",
        "total_records": len(records),
        "clean_rows": len(clean_df),
    }
    generate_phase1_report(
        report_path=settings.paths.baseline_report,
        source_summary=source_summary,
        metrics=evaluation_bundle.summary,
        quality=quality_res,
        freshness=freshness_res,
    )
    logger.info(f"Phase 1 Baseline Report saved to {settings.paths.baseline_report}")
    print("\n=======================================================")
    print("PHASE 1 BASELINE PIPELINE COMPLETED SUCCESSFULLY!")
    print(f"Retrieval Hit Rate: {evaluation_bundle.summary.get('retrieval_hit_rate', 0.0) * 100:.1f}%")
    print(f"Mean Token F1:      {evaluation_bundle.summary.get('mean_token_f1', 0.0):.4f}")
    print(f"LLM Judge Accuracy: {evaluation_bundle.summary.get('judge_accuracy', 0.0) * 100:.1f}%")
    print(f"Quality Gate Pass:  {quality_res.get('gx_success', False)}")
    print(f"Freshness SLA Pass: {freshness_res.get('is_fresh', False)}")
    print("=======================================================\n")


if __name__ == "__main__":
    main()
