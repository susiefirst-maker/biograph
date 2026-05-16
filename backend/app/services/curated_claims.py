"""Curated claims loader — applies data/curated/<drug>_claims.yml.

Each claim references an article by slug; loader resolves slug →
article.id via title/url lookup. Claims link to Drug via the polymorphic
entity_claim_link junction (entity_type='drug').
"""

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Article, Claim, Drug
from app.models._helpers import ClaimType
from app.models.relationships import entity_claim_link


CURATED_DIR = Path(__file__).resolve().parents[3] / "data" / "curated"
CLAIMS_FILES = sorted(CURATED_DIR.glob("*_claims.yml"))

# For slug → article_id resolution. The articles YAML uses id_slug as a
# local identifier; we index by the combination of title + url that the
# articles YAML provides alongside id_slug.
# Simpler approach: re-read articles YAML and build slug→url map.
ARTICLES_FILE = CURATED_DIR / "humira_articles.yml"


def load_curated_claims() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in CLAIMS_FILES:
        if not path.exists():
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        out.extend(doc.get("drugs") or [])
    return out


def _load_article_slug_to_url() -> dict[str, str]:
    """Read humira_articles.yml and build slug → url index."""
    if not ARTICLES_FILE.exists():
        return {}
    doc = yaml.safe_load(ARTICLES_FILE.read_text()) or {}
    mapping: dict[str, str] = {}
    for drug in doc.get("drugs") or []:
        for a in drug.get("articles") or []:
            slug = a.get("id_slug")
            url = a.get("url")
            if slug and url:
                mapping[slug] = url
    return mapping


async def _resolve_article_id(session: AsyncSession, url: str) -> Any | None:
    row = await session.scalar(select(Article).where(Article.url == url))
    return row.id if row else None


async def apply_curated_claims(session: AsyncSession) -> int:
    """Upsert claims + link to Drug via entity_claim_link. Returns count persisted."""
    entries = load_curated_claims()
    slug_to_url = _load_article_slug_to_url()
    total = 0

    for drug_entry in entries:
        chembl_id = drug_entry.get("chembl_id")
        claims = drug_entry.get("claims") or []
        if not chembl_id or not claims:
            continue

        drug = await session.scalar(select(Drug).where(Drug.chembl_id == chembl_id))
        if drug is None:
            continue

        for c in claims:
            statement = c.get("statement")
            if not statement:
                continue

            # Resolve article
            article_id = None
            if article_slug := c.get("article_slug"):
                if article_url := slug_to_url.get(article_slug):
                    article_id = await _resolve_article_id(session, article_url)

            try:
                claim_type = ClaimType(c["claim_type"].lower())
            except (ValueError, KeyError):
                continue

            # Natural dedup: (article_id, statement[:200])
            existing = await session.scalar(
                select(Claim).where(
                    and_(
                        Claim.article_id == article_id,
                        Claim.statement == statement,
                    )
                )
            )

            if existing is None:
                claim = Claim(
                    statement=statement,
                    language=c.get("language") or "en",
                    claim_type=claim_type,
                    evidence_basis=c.get("evidence_basis"),
                    confidence=c.get("confidence"),
                    article_id=article_id,
                    entities_mentioned=c.get("entities_mentioned") or [],
                    field_provenance={"_curated_source": "data/curated/humira_claims.yml"},
                )
                session.add(claim)
                await session.flush()
                claim_id = claim.id
                total += 1
            else:
                existing.evidence_basis = c.get("evidence_basis") or existing.evidence_basis
                claim_id = existing.id

            # Link claim → drug via polymorphic junction
            stmt = pg_insert(entity_claim_link).values(
                claim_id=claim_id,
                entity_type="drug",
                entity_id=drug.id,
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["claim_id", "entity_type", "entity_id"]
            )
            await session.execute(stmt)

    await session.flush()
    return total
