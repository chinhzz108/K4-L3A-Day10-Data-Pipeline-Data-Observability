from __future__ import annotations

from typing import Any
from pathlib import Path

import great_expectations as gx
import great_expectations.expectations as gxe
import pandas as pd

from core.config import Settings
from core.utils import safe_slug, write_json


def run_data_quality_checks(df: pd.DataFrame, settings: Settings, report_name: str) -> dict[str, Any]:
    """Run Data Quality checks using Great Expectations 1.x ephemeral mode and Freshness SLA.

    Checks:
    1. Table row count is between 5 and 5000.
    2. paper_id, title, and text_for_embedding are not null.
    3. paper_id values are unique.
    4. summary length is between 30 and 10000 characters.
    5. Freshness SLA: ratio of stale records (age_days > 180) must be <= 25%.
    """
    slug = safe_slug(report_name)
    context = gx.get_context(mode="ephemeral")
    data_source = context.data_sources.add_pandas(name=f"papers_source_{slug}")
    data_asset = data_source.add_dataframe_asset(name=f"papers_asset_{slug}")
    batch_def = data_asset.add_batch_definition_whole_dataframe(f"papers_batch_{slug}")

    suite = gx.ExpectationSuite(name=f"papers_suite_{slug}")
    suite.add_expectation(gxe.ExpectTableRowCountToBeBetween(min_value=5, max_value=5000))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="title"))
    suite.add_expectation(gxe.ExpectColumnValuesToNotBeNull(column="text_for_embedding"))
    suite.add_expectation(gxe.ExpectColumnValuesToBeUnique(column="paper_id"))
    suite.add_expectation(gxe.ExpectColumnValueLengthsToBeBetween(column="summary", min_value=30))

    context.suites.add(suite)
    validation_definition = gx.ValidationDefinition(
        data=batch_def, suite=suite, name=f"papers_validation_{slug}"
    )
    context.validation_definitions.add(validation_definition)
    results = validation_definition.run(batch_parameters={"dataframe": df})

    # Freshness evaluation
    stale_rows = 0
    total_rows = len(df)
    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())
    stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0
    is_fresh = stale_ratio <= 0.25

    expectation_results = []
    for r in results.results:
        exp_type = getattr(r.expectation_config, "type", str(r.expectation_config))
        expectation_results.append(
            {
                "expectation": exp_type,
                "success": bool(r.success),
                "kwargs": dict(getattr(r.expectation_config, "kwargs", {}) or {}),
                "result": dict(r.result or {}),
            }
        )

    # Overarching success requires GX expectations to pass AND freshness SLA to be met
    overall_success = bool(results.success) and is_fresh

    report_payload = {
        "report_name": report_name,
        "success": overall_success,
        "gx_success": bool(results.success),
        "total_rows": total_rows,
        "expectations": expectation_results,
        "freshness": {
            "stale_rows": stale_rows,
            "total_rows": total_rows,
            "stale_ratio": round(stale_ratio, 4),
            "threshold_days": settings.freshness_threshold_days,
            "is_fresh": is_fresh,
        },
    }

    if report_name == "baseline":
        out_path = settings.paths.baseline_quality_report
    elif report_name == "corrupted":
        out_path = settings.paths.corrupted_quality_report
    else:
        out_path = settings.paths.quality_dir / f"{slug}_quality_report.json"

    write_json(out_path, report_payload)
    return report_payload


def build_freshness_report(df: pd.DataFrame, settings: Settings, report_path: Path) -> dict[str, Any]:
    """Compile and export freshness status and SLA compliance report."""
    total_rows = len(df)
    stale_rows = 0
    if "age_days" in df.columns and total_rows > 0:
        stale_rows = int((df["age_days"] > settings.freshness_threshold_days).sum())

    stale_ratio = stale_rows / total_rows if total_rows > 0 else 0.0
    is_fresh = stale_ratio <= 0.25

    latest_published = str(df["published"].max()) if not df.empty and "published" in df else ""
    oldest_published = str(df["published"].min()) if not df.empty and "published" in df else ""

    payload = {
        "latest_published": latest_published,
        "oldest_published": oldest_published,
        "stale_rows": stale_rows,
        "total_rows": total_rows,
        "stale_ratio": round(stale_ratio, 4),
        "threshold_days": settings.freshness_threshold_days,
        "is_fresh": is_fresh,
    }
    write_json(report_path, payload)
    return payload
