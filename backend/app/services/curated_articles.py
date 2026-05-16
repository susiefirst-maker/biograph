"""Curated articles loader — applies data/curated/humira_articles.yml
(and future <drug>_articles.yml) into Article rows.

Natural key: url_hash (sha256 of url, truncated to 64 chars). Idempotent.
Phase 2+ will extend with link-to-drug via claim/entity-relationship paths;
today the articles stand alone and are referenced via source_refs.
"""

import hashlib
from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article


CURATED_DIR = Path(__file__).resolve().parents[3] / "data" / "curated"
ARTICLE_FILES = sorted(CURATED_DIR.glob("*_articles.yml"))


def _parse_date(raw: Any) -> date | None:
    if isinstance(raw, date):
        return raw
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date()
    except ValueError:
        return None


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.encode("utf-8")).hexdigest()[:64]


def load_curated_articles() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in ARTICLE_FILES:
        if not path.exists():
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        out.extend(doc.get("drugs") or [])
    return out


async def apply_curated_articles(session: AsyncSession) -> int:
    """Upsert articles by url_hash. Returns count persisted."""
    entries = load_curated_articles()
    total = 0

    for drug_entry in entries:
        for a in drug_entry.get("articles") or []:
            url = a.get("url")
            if not url:
                continue
            url_hash = a.get("url_hash") or _url_hash(url)

            existing = await session.scalar(
                select(Article).where(Article.url_hash == url_hash)
            )
            if existing is None:
                session.add(
                    Article(
                        url_hash=url_hash,
                        url=url,
                        title=a.get("title"),
                        source_name=a.get("source_name"),
                        source_type=a.get("source_type"),
                        language=a.get("language") or "en",
                        publish_date=_parse_date(a.get("publish_date")),
                        credibility_tier=a.get("credibility_tier"),
                        cached_content=a.get("summary"),  # summary serves as cached content for claim extraction
                        field_provenance={"_curated_source": "data/curated/humira_articles.yml"},
                    )
                )
                total += 1
            else:
                # Update mutable fields
                existing.title = a.get("title") or existing.title
                existing.source_name = a.get("source_name") or existing.source_name
                existing.credibility_tier = a.get("credibility_tier") or existing.credibility_tier
                if a.get("summary") and not existing.cached_content:
                    existing.cached_content = a["summary"]

    await session.flush()
    return total
