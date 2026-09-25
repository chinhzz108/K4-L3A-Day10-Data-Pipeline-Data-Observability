from __future__ import annotations

from typing import Any
from pathlib import Path

import pandas as pd

from core.utils import first_sentence, write_json


def build_test_set(df: pd.DataFrame, output_path: Path) -> list[dict[str, Any]]:
    """Build evaluation test set with 10 questions across 4 distinct tasks:

    1. summary (3 questions)
    2. authors (3 questions)
    3. date (2 questions)
    4. categories (2 questions)

    Each test item contains:
    - id: eval_001 .. eval_010
    - question_type: 'summary' | 'authors' | 'date' | 'categories'
    - question: formulated question referencing exact title in single quotes
    - ground_truth: expected answer string
    - ground_truth_doc_ids: list containing the paper DOI/ID
    """
    if len(df) < 10:
        raise ValueError(f"DataFrame must contain at least 10 records to build test set, got {len(df)}")

    # Distinct papers for the 10 questions
    sample_rows = df.iloc[:10].to_dict(orient="records")

    # Map question types across the 10 questions: 3 summary, 3 authors, 2 date, 2 categories
    type_assignments = [
        "summary",
        "summary",
        "summary",
        "authors",
        "authors",
        "authors",
        "date",
        "date",
        "categories",
        "categories",
    ]

    test_items: list[dict[str, Any]] = []

    for index, (row, qtype) in enumerate(zip(sample_rows, type_assignments), start=1):
        item_id = f"eval_{index:03d}"
        title = row["title"]
        paper_id = row["paper_id"]

        if qtype == "summary":
            question = f"What is the summary of the paper '{title}'?"
            ground_truth = first_sentence(str(row.get("summary", "")))
        elif qtype == "authors":
            question = f"Who authored the paper '{title}'?"
            ground_truth = str(row.get("authors_joined", ""))
        elif qtype == "date":
            question = f"When was the paper '{title}' published?"
            ground_truth = str(row.get("published", ""))
        elif qtype == "categories":
            question = f"What categories does the paper '{title}' belong to?"
            ground_truth = str(row.get("categories_joined", ""))
        else:
            question = f"Tell me about the paper '{title}'"
            ground_truth = first_sentence(str(row.get("summary", "")))

        test_items.append(
            {
                "id": item_id,
                "question_type": qtype,
                "question": question,
                "ground_truth": ground_truth,
                "ground_truth_doc_ids": [paper_id],
            }
        )

    write_json(output_path, test_items)
    return test_items
