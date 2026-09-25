from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
import re
from typing import Any

import requests

from core.config import Settings
from core.utils import normalize_whitespace, read_json, write_json


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    title: str
    summary: str
    authors: list[str]
    categories: list[str]
    primary_category: str
    published: str
    updated: str
    abs_url: str
    pdf_url: str
    comment: str


def _clean_abstract(raw: str) -> str:
    if not raw:
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", raw)
    return normalize_whitespace(cleaned)


def _format_date(date_parts: list[Any] | None) -> str:
    if not date_parts or not date_parts[0]:
        return datetime.now().strftime("%Y-%m-%d")
    first = date_parts[0]
    year = first[0] if len(first) > 0 else 2026
    month = first[1] if len(first) > 1 else 1
    day = first[2] if len(first) > 2 else 1
    return f"{year:04d}-{month:02d}-{day:02d}"


def parse_crossref_payload(payload: dict) -> list[PaperRecord]:
    """Parse Crossref payload into a list of PaperRecord.

    Extracts DOI, title, abstract (stripping XML/JATS tags), authors,
    categories, published/updated dates, URLs and comments.
    """
    items = payload.get("message", {}).get("items", [])
    records: list[PaperRecord] = []
    for item in items:
        paper_id = item.get("DOI", "").strip() or item.get("id", "").strip()
        title_list = item.get("title", [])
        title = normalize_whitespace(title_list[0]) if title_list else ""
        if not paper_id or not title:
            continue

        raw_abstract = item.get("abstract", "")
        summary = _clean_abstract(raw_abstract)

        authors: list[str] = []
        for author in item.get("author", []):
            given = author.get("given", "").strip()
            family = author.get("family", "").strip()
            name = author.get("name", "").strip()
            full = f"{given} {family}".strip() or name
            if full:
                authors.append(full)

        categories = [normalize_whitespace(c) for c in item.get("subject", []) if c]
        primary_category = categories[0] if categories else "General"

        published_parts = (
            item.get("published", {}).get("date-parts")
            or item.get("created", {}).get("date-parts")
            or item.get("issued", {}).get("date-parts")
        )
        published = _format_date(published_parts)

        updated_parts = item.get("updated", {}).get("date-parts") or published_parts
        updated = _format_date(updated_parts)

        abs_url = item.get("URL", f"https://doi.org/{paper_id}")
        pdf_url = abs_url
        for link in item.get("link", []):
            if link.get("content-type") == "application/pdf":
                pdf_url = link.get("URL", abs_url)
                break

        comment = f"Crossref record {paper_id}"

        records.append(
            PaperRecord(
                paper_id=paper_id,
                title=title,
                summary=summary,
                authors=authors,
                categories=categories,
                primary_category=primary_category,
                published=published,
                updated=updated,
                abs_url=abs_url,
                pdf_url=pdf_url,
                comment=comment,
            )
        )
    return records


def fetch_source_records(settings: Settings) -> list[PaperRecord]:
    """Fetch from source API or fallback to local snapshot, save raw response and records."""
    payload: dict | None = None

    if settings.refresh_source:
        try:
            url = "https://api.crossref.org/works"
            params = {
                "query": settings.source_query,
                "filter": settings.source_filter,
                "rows": settings.max_results,
            }
            headers = {"User-Agent": "Day10-DataPipelineLab/1.0 (mailto:student@lab.edu)"}
            resp = requests.get(url, params=params, headers=headers, timeout=15)
            if resp.status_code == 200:
                payload = resp.json()
                write_json(settings.paths.raw_api_response, payload)
        except Exception:
            payload = None

    if payload is None:
        if settings.paths.raw_api_response.exists():
            payload = read_json(settings.paths.raw_api_response)
        else:
            raise FileNotFoundError(f"Raw API response not found at {settings.paths.raw_api_response}")

    records = parse_crossref_payload(payload)
    write_json(settings.paths.raw_records_json, [asdict(r) for r in records])
    return records


def load_raw_records(path: Path) -> list[PaperRecord]:
    """Read JSON snapshot and map into `PaperRecord` objects."""
    data = read_json(path)
    return [PaperRecord(**item) for item in data]
