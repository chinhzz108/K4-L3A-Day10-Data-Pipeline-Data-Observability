from __future__ import annotations

from datetime import datetime
from typing import Any

import pandas as pd

from core.utils import compact_join, normalize_whitespace
from ingestion.crossref import PaperRecord


def build_clean_dataframe(records: list[PaperRecord], run_date: datetime) -> pd.DataFrame:
    """Clean raw records into a prepared DataFrame ready for embedding and indexing.

    Steps:
    1. Normalize text fields (title, summary, authors, categories).
    2. Parse published/updated dates and calculate age_days relative to run_date.
    3. Generate helper columns: authors_joined, categories_joined, summary_chars, text_for_embedding.
    4. Remove invalid entries and deduplicate by paper_id.
    5. Sort cleanly and reset index.
    """
    rows: list[dict[str, Any]] = []

    for r in records:
        paper_id = normalize_whitespace(r.paper_id)
        title = normalize_whitespace(r.title)
        if not paper_id or not title:
            continue

        summary = normalize_whitespace(r.summary)
        authors = [normalize_whitespace(a) for a in r.authors if normalize_whitespace(a)]
        categories = [normalize_whitespace(c) for c in r.categories if normalize_whitespace(c)]
        authors_joined = compact_join(authors, sep=", ")
        categories_joined = compact_join(categories, sep=", ")

        # Parse published date and compute age_days
        try:
            pub_date = datetime.strptime(r.published[:10], "%Y-%m-%d").date()
        except Exception:
            pub_date = run_date.date()

        run_d = run_date.date() if hasattr(run_date, "date") else run_date
        age_days = max(0, (run_d - pub_date).days)

        text_for_embedding = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {r.published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )

        rows.append(
            {
                "paper_id": paper_id,
                "title": title,
                "summary": summary,
                "authors": authors,
                "categories": categories,
                "primary_category": r.primary_category or (categories[0] if categories else "General"),
                "published": r.published,
                "updated": r.updated,
                "abs_url": r.abs_url,
                "pdf_url": r.pdf_url,
                "comment": r.comment,
                "age_days": age_days,
                "authors_joined": authors_joined,
                "categories_joined": categories_joined,
                "summary_chars": len(summary),
                "text_for_embedding": text_for_embedding,
            }
        )

    df = pd.DataFrame(rows)
    if not df.empty:
        df = df.drop_duplicates(subset=["paper_id"], keep="first")
        df = df.sort_values(by=["published", "paper_id"], ascending=[False, True]).reset_index(drop=True)
    return df
