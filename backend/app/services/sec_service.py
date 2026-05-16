"""SEC-driven Company upsert — resolves by CIK when present, else by name."""

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company


async def upsert_company_from_sec(
    session: AsyncSession, normalized: dict[str, Any]
) -> Company | None:
    """Upsert a Company row from an SEC EDGAR payload.

    Match priority:
      1. sec_cik (authoritative — unique indexed column).
      2. Exact case-insensitive name match (merges duplicate rows sponsors
         from CT.gov created without CIK).
    """
    payload = normalized.get("company")
    if not payload:
        return None

    cik = payload["sec_cik"]
    existing = await session.scalar(select(Company).where(Company.sec_cik == cik))
    if existing:
        existing.ticker = payload["ticker"]
        existing.name = payload["name"] or existing.name
        return existing

    # Try name match — promotes a CT.gov-sourced sponsor row into an
    # SEC-resolved Company without losing existing trial links.
    by_name = await session.scalar(
        select(Company).where(func.lower(Company.name) == (payload["name"] or "").lower())
    )
    if by_name:
        by_name.sec_cik = cik
        by_name.ticker = payload["ticker"]
        return by_name

    company = Company(
        sec_cik=cik,
        ticker=payload["ticker"],
        name=payload["name"],
    )
    session.add(company)
    await session.flush()
    return company
