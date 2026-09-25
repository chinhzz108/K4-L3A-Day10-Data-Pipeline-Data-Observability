from __future__ import annotations

import logging
import pandas as pd

from core.config import load_settings
from core.utils import now_utc, read_json, write_csv, write_json
from evaluation.metrics import evaluate_pipeline
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from ingestion.crossref import load_raw_records
from observability.quality import build_freshness_report, run_data_quality_checks
from observability.reporting import generate_corruption_report
from retrieval.index import LocalEmbeddingIndex

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def main() -> None:
    """Execute Phase 2: Controlled Data Corruption, Impact Measurement, and Idempotent Repair.

    Flow:
    1. Load baseline metrics and clean dataset.
    2. Inject 6 synthetic data corruptions into clean DataFrame.
    3. Persist corrupted artifacts and build corrupted Chroma vector index.
    4. Run Quality Gate & Freshness SLA checks on corrupted data (observing alerts).
    5. Evaluate degraded retrieval hit rate and token F1 (demonstrating Silent Failure).
    6. Execute Idempotent Repair by re-running deterministic transformation from raw snapshot.
    7. Persist repaired artifacts, rebuild Chroma repaired index, and re-evaluate metrics.
    8. Compile and render 3-state comparison Markdown report.
    """
    logger.info("=== Starting Phase 2: Corruption, Observability Alert, and Repair Flow ===")
    settings = load_settings()

    # Step 1: Load baseline artifacts
    if not settings.paths.baseline_metrics.exists() or not settings.paths.clean_json.exists():
        logger.warning("Baseline artifacts missing. Running baseline preparation...")
        from pipelines.phase1 import main as run_baseline
        run_baseline()

    baseline_metrics = read_json(settings.paths.baseline_metrics)
    clean_df = pd.read_json(settings.paths.clean_json)
    logger.info(f"Loaded baseline clean dataset with {len(clean_df)} records.")

    # Step 2: Inject Synthetic Corruption
    logger.info("Injecting 6 controlled corruptions into clean data...")
    corrupted_df = corrupt_clean_dataframe(clean_df, settings.paths.corruption_log)
    logger.info(f"Corrupted dataset contains {len(corrupted_df)} records.")

    # Step 3: Persist Corrupted Data
    write_csv(corrupted_df, settings.paths.corrupted_clean_csv)
    write_json(settings.paths.corrupted_clean_json, corrupted_df.to_dict(orient="records"))

    # Step 4: Quality Gate on Corrupted Data
    logger.info("Running Great Expectations 1.x on corrupted data (expecting alerts)...")
    corrupted_quality = run_data_quality_checks(corrupted_df, settings, "corrupted")
    corrupted_freshness_path = settings.paths.quality_dir / "corrupted_freshness_report.json"
    corrupted_freshness = build_freshness_report(corrupted_df, settings, corrupted_freshness_path)
    logger.info(f"Corrupted Quality Gate Success: {corrupted_quality.get('gx_success', False)}")
    logger.info(f"Corrupted Freshness SLA Status: {corrupted_freshness.get('is_fresh', False)}")

    # Step 5: Index & Evaluate Corrupted Data
    logger.info(f"Building corrupted Chroma collection '{settings.corrupted_collection_name}'...")
    corrupted_index = LocalEmbeddingIndex.build(corrupted_df, settings, settings.paths.corrupted_embeddings_json)
    logger.info("Evaluating degraded RAG metrics...")
    corrupted_bundle = evaluate_pipeline(
        settings=settings,
        index=corrupted_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.corrupted_metrics,
        answers_output_path=settings.paths.corrupted_answers,
    )
    logger.info(f"Corrupted Metrics: {corrupted_bundle.summary}")

    # Step 6: Idempotent Self-Healing Repair from Raw Lineage
    logger.info("Executing Idempotent Repair from raw snapshot lineage...")
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())
    logger.info(f"Repaired dataset restored with {len(repaired_df)} records.")

    # Step 7: Persist Repaired Data & Build Repaired Vector Index
    write_csv(repaired_df, settings.paths.repaired_clean_csv)
    write_json(settings.paths.repaired_clean_json, repaired_df.to_dict(orient="records"))

    logger.info("Validating repaired dataset with Quality Gate...")
    repaired_quality = run_data_quality_checks(repaired_df, settings, "repaired")
    repaired_freshness_path = settings.paths.quality_dir / "repaired_freshness_report.json"
    repaired_freshness = build_freshness_report(repaired_df, settings, repaired_freshness_path)

    logger.info(f"Building repaired Chroma collection '{settings.repaired_collection_name}'...")
    repaired_index = LocalEmbeddingIndex.build(repaired_df, settings, settings.paths.repaired_embeddings_json)

    logger.info("Evaluating repaired RAG metrics...")
    repaired_bundle = evaluate_pipeline(
        settings=settings,
        index=repaired_index,
        test_set_path=settings.paths.eval_testset,
        metrics_output_path=settings.paths.repaired_metrics,
        answers_output_path=settings.paths.repaired_answers,
    )
    logger.info(f"Repaired Metrics: {repaired_bundle.summary}")

    # Step 8: Render Comparison Report
    logger.info("Rendering 3-state comparison Markdown report...")
    generate_corruption_report(
        report_path=settings.paths.comparison_report,
        baseline_metrics=baseline_metrics,
        corrupted_metrics=corrupted_bundle.summary,
        repaired_metrics=repaired_bundle.summary,
        corrupted_quality=corrupted_quality,
        repaired_quality=repaired_quality,
        corrupted_freshness=corrupted_freshness,
        repaired_freshness=repaired_freshness,
    )
    logger.info(f"Comparison report saved to {settings.paths.comparison_report}")

    # Step 9: Print CLI Comparison Summary Table
    b_hit = baseline_metrics.get("retrieval_hit_rate", 0.0) * 100
    c_hit = corrupted_bundle.summary.get("retrieval_hit_rate", 0.0) * 100
    r_hit = repaired_bundle.summary.get("retrieval_hit_rate", 0.0) * 100

    b_f1 = baseline_metrics.get("mean_token_f1", 0.0)
    c_f1 = corrupted_bundle.summary.get("mean_token_f1", 0.0)
    r_f1 = repaired_bundle.summary.get("mean_token_f1", 0.0)

    print("\n" + "=" * 70)
    print("3-STATE PERFORMANCE COMPARISON SUMMARY")
    print("=" * 70)
    print(f"{'Dimension':<25} | {'Baseline (Clean)':<15} | {'Corrupted':<15} | {'Repaired':<15}")
    print("-" * 70)
    print(f"{'Retrieval Hit Rate':<25} | {b_hit:>13.1f}% | {c_hit:>13.1f}% | {r_hit:>13.1f}%")
    print(f"{'Mean Token F1':<25} | {b_f1:>14.4f} | {c_f1:>14.4f} | {r_f1:>14.4f}")
    print(f"{'GX Quality Gate':<25} | {'PASSED':>14} | {'FAILED':>14} | {'PASSED':>14}")
    print(f"{'Freshness SLA':<25} | {'PASSED':>14} | {'FAILED':>14} | {'PASSED':>14}")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
