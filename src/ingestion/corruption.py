from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from core.utils import write_json


def corrupt_clean_dataframe(df: pd.DataFrame, output_log_path: Path) -> pd.DataFrame:
    """Inject 6 controlled data corruptions into a clean DataFrame to simulate production failures:

    1. Drop latest records: Discard top 20% newest publications (simulating ingestion staleness).
    2. Blank summary: Set summary to empty string on select rows (causing length expectation failures).
    3. Inject noise: Add garbage characters into summary on select rows (degrading embedding semantics).
    4. Truncate title: Truncate title to < 8 characters on select rows.
    5. Stale date: Shift publication dates back by 365+ days on > 30% of rows (violating Freshness SLA).
    6. Duplicate rows: Append duplicate records (violating uniqueness expectation on paper_id).

    Reconstructs `text_for_embedding` and writes corruption audit log to `output_log_path`.
    """
    corrupted = df.copy()
    logs: list[dict[str, Any]] = []

    # 1. Drop latest 20% of records
    drop_count = max(1, int(len(corrupted) * 0.20))
    dropped_ids = corrupted.iloc[:drop_count]["paper_id"].tolist()
    corrupted = corrupted.iloc[drop_count:].copy().reset_index(drop=True)
    logs.append(
        {
            "corruption_type": "drop_latest_records",
            "count": drop_count,
            "target_ids": dropped_ids,
            "details": f"Dropped newest {drop_count} records (20%) to simulate ingestion pipeline gap.",
        }
    )

    n_rows = len(corrupted)

    # 2. Blank summary on 2 records
    blank_indices = [0, 1] if n_rows >= 2 else [0]
    blanked_ids = []
    for idx in blank_indices:
        corrupted.at[idx, "summary"] = ""
        blanked_ids.append(corrupted.at[idx, "paper_id"])
    logs.append(
        {
            "corruption_type": "blank_summary",
            "count": len(blank_indices),
            "target_ids": blanked_ids,
            "details": f"Erased summary text on {len(blank_indices)} records (GX summary length violation).",
        }
    )

    # 3. Inject noise on 2 records
    noise_indices = [2, 3] if n_rows >= 4 else ([1] if n_rows >= 2 else [0])
    noise_ids = []
    noise_suffix = " ### CORRUPTED_GARBAGE_NOISE_#$@%&!_INVALID_TOKEN_SEQUENCE ###"
    for idx in noise_indices:
        corrupted.at[idx, "summary"] = str(corrupted.at[idx, "summary"]) + noise_suffix
        noise_ids.append(corrupted.at[idx, "paper_id"])
    logs.append(
        {
            "corruption_type": "inject_noise",
            "count": len(noise_indices),
            "target_ids": noise_ids,
            "details": f"Appended adversarial noise tokens to summary on {len(noise_indices)} records.",
        }
    )

    # 4. Truncate title on 2 records (< 8 characters)
    trunc_indices = [4, 5] if n_rows >= 6 else [idx for idx in [0, 1] if idx < n_rows]
    trunc_ids = []
    for idx in trunc_indices:
        current_title = str(corrupted.at[idx, "title"])
        corrupted.at[idx, "title"] = current_title[:6] if len(current_title) >= 6 else "Bad"
        trunc_ids.append(corrupted.at[idx, "paper_id"])
    logs.append(
        {
            "corruption_type": "truncate_title",
            "count": len(trunc_indices),
            "target_ids": trunc_ids,
            "details": f"Truncated title to < 8 chars on {len(trunc_indices)} records.",
        }
    )

    # 5. Stale date: shift publication dates back by 365 days on 40% of records
    stale_count = max(2, int(n_rows * 0.40))
    stale_indices = list(range(n_rows - stale_count, n_rows))
    stale_ids = []
    for idx in stale_indices:
        orig_published = str(corrupted.at[idx, "published"])
        try:
            p_date = datetime.strptime(orig_published[:10], "%Y-%m-%d").date()
            shifted = p_date - timedelta(days=365)
            corrupted.at[idx, "published"] = shifted.strftime("%Y-%m-%d")
        except Exception:
            corrupted.at[idx, "published"] = "2023-01-01"
        corrupted.at[idx, "age_days"] = int(corrupted.at[idx, "age_days"]) + 365
        stale_ids.append(corrupted.at[idx, "paper_id"])
    logs.append(
        {
            "corruption_type": "stale_date",
            "count": len(stale_indices),
            "target_ids": stale_ids,
            "details": f"Shifted publication dates back by 365 days on {len(stale_indices)} records to trigger Freshness SLA breach.",
        }
    )

    # 6. Duplicate rows: duplicate 2 existing rows
    dup_indices = [0, 1] if n_rows >= 2 else [0]
    dup_rows = corrupted.iloc[dup_indices].copy()
    corrupted = pd.concat([corrupted, dup_rows], ignore_index=True)
    logs.append(
        {
            "corruption_type": "duplicate_rows",
            "count": len(dup_indices),
            "target_ids": dup_rows["paper_id"].tolist(),
            "details": f"Duplicated {len(dup_indices)} rows (GX paper_id uniqueness violation).",
        }
    )

    # 7. Rebuild summary_chars and text_for_embedding for all rows
    rebuilt_embedding_texts = []
    summary_lengths = []
    for _, row in corrupted.iterrows():
        title = row["title"]
        authors_joined = row.get("authors_joined", "")
        published = row.get("published", "")
        categories_joined = row.get("categories_joined", "")
        summary = row.get("summary", "")
        text = (
            f"Title: {title}\n"
            f"Authors: {authors_joined}\n"
            f"Published: {published}\n"
            f"Categories: {categories_joined}\n"
            f"Summary: {summary}"
        )
        rebuilt_embedding_texts.append(text)
        summary_lengths.append(len(str(summary)))

    corrupted["text_for_embedding"] = rebuilt_embedding_texts
    corrupted["summary_chars"] = summary_lengths

    # 8. Write audit log
    write_json(output_log_path, logs)
    return corrupted
