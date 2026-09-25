from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
import pandas as pd

from core.config import load_settings
from core.utils import now_utc
from ingestion.crossref import PaperRecord, load_raw_records, parse_crossref_payload
from ingestion.cleaning import build_clean_dataframe
from ingestion.corruption import corrupt_clean_dataframe
from evaluation.testset import build_test_set
from observability.quality import build_freshness_report, run_data_quality_checks
from retrieval.index import LocalEmbeddingIndex
from retrieval.qa import answer_question


@pytest.fixture
def settings():
    return load_settings()


@pytest.fixture
def sample_payload():
    return {
        "status": "ok",
        "message": {
            "total-results": 2,
            "items": [
                {
                    "DOI": "10.1000/182",
                    "title": ["Test Paper on RAG Systems"],
                    "abstract": "<jats:p>This is a valid scholarly abstract discussing retrieval-augmented generation and quality gates in modern AI pipelines.</jats:p>",
                    "author": [{"given": "Alice", "family": "Smith"}],
                    "subject": ["Computer Science", "Artificial Intelligence"],
                    "published": {"date-parts": [[2026, 6, 1]]},
                    "created": {"date-parts": [[2026, 6, 1]]},
                    "URL": "https://doi.org/10.1000/182",
                },
                {
                    "DOI": "10.1000/183",
                    "title": ["Data Observability in MLOps"],
                    "abstract": "<jats:p>Exploring continuous data monitoring, schema validation, and drift detection mechanisms.</jats:p>",
                    "author": [{"given": "Bob", "family": "Jones"}],
                    "subject": ["Software Engineering"],
                    "published": {"date-parts": [[2026, 5, 15]]},
                    "created": {"date-parts": [[2026, 5, 15]]},
                    "URL": "https://doi.org/10.1000/183",
                },
            ],
        },
    }


def test_parse_crossref_payload(sample_payload):
    records = parse_crossref_payload(sample_payload)
    assert len(records) == 2
    assert records[0].paper_id == "10.1000/182"
    assert "Test Paper on RAG Systems" in records[0].title
    assert "<jats:p>" not in records[0].summary
    assert "Alice Smith" in records[0].authors
    assert records[0].primary_category == "Computer Science"


def test_load_raw_records(settings):
    assert settings.paths.raw_records_json.exists()
    records = load_raw_records(settings.paths.raw_records_json)
    assert len(records) >= 10
    assert all(isinstance(r, PaperRecord) for r in records)


def test_build_clean_dataframe(settings):
    records = load_raw_records(settings.paths.raw_records_json)
    df = build_clean_dataframe(records, now_utc())

    assert not df.empty
    assert "text_for_embedding" in df.columns
    assert "age_days" in df.columns
    assert "summary_chars" in df.columns
    assert df["paper_id"].is_unique
    assert all(df["age_days"] >= 0)
    assert len(df) == 24


def test_great_expectations_quality_gate(settings):
    records = load_raw_records(settings.paths.raw_records_json)
    df = build_clean_dataframe(records, now_utc())

    report = run_data_quality_checks(df, settings, "test_clean")
    assert report["gx_success"] is True
    assert report["freshness"]["is_fresh"] is True
    assert report["success"] is True


def test_freshness_sla_report(settings, tmp_path):
    records = load_raw_records(settings.paths.raw_records_json)
    df = build_clean_dataframe(records, now_utc())
    report_file = tmp_path / "freshness_test.json"

    report = build_freshness_report(df, settings, report_file)
    assert report_file.exists()
    assert report["total_rows"] == 24
    assert report["is_fresh"] is True
    assert report["stale_ratio"] <= 0.25


def test_build_test_set(settings, tmp_path):
    records = load_raw_records(settings.paths.raw_records_json)
    df = build_clean_dataframe(records, now_utc())
    testset_path = tmp_path / "testset.json"

    testset = build_test_set(df, testset_path)
    assert len(testset) == 10
    types = {item["question_type"] for item in testset}
    assert {"summary", "authors", "date", "categories"}.issubset(types)
    assert all("id" in item and "question" in item and "ground_truth" in item for item in testset)


def test_corruption_suite_triggers_observability_alerts(settings, tmp_path):
    records = load_raw_records(settings.paths.raw_records_json)
    clean_df = build_clean_dataframe(records, now_utc())
    log_path = tmp_path / "corruption_log.json"

    corrupted_df = corrupt_clean_dataframe(clean_df, log_path)
    assert log_path.exists()
    assert len(corrupted_df) > 0

    # Observability gate must detect corruption
    corrupted_report = run_data_quality_checks(corrupted_df, settings, "test_corrupted")
    assert corrupted_report["gx_success"] is False
    assert corrupted_report["freshness"]["is_fresh"] is False
    assert corrupted_report["success"] is False


def test_idempotent_repair_restores_integrity(settings, tmp_path):
    records = load_raw_records(settings.paths.raw_records_json)
    clean_df = build_clean_dataframe(records, now_utc())

    # Corrupt
    corrupted_df = corrupt_clean_dataframe(clean_df, tmp_path / "log.json")
    assert len(corrupted_df) != len(clean_df) or not corrupted_df["paper_id"].is_unique

    # Repair from raw lineage
    raw_records = load_raw_records(settings.paths.raw_records_json)
    repaired_df = build_clean_dataframe(raw_records, now_utc())

    assert len(repaired_df) == len(clean_df)
    assert set(repaired_df["paper_id"]) == set(clean_df["paper_id"])

    repaired_report = run_data_quality_checks(repaired_df, settings, "test_repaired")
    assert repaired_report["gx_success"] is True
    assert repaired_report["freshness"]["is_fresh"] is True
