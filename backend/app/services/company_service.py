"""Company upsert helpers — ticker-first, then case-insensitive name.

Without ticker disambiguation, different ingesters create duplicate
Company rows for the same real-world entity ("AbbVie Inc." from SEC,
"ABBVIE INC" from CT.gov, "AbbVie" from curated YAML). Callers that
know the ticker should pass it; the helper will stamp ticker on the
returned row if missing, giving downstream lookups a canonical handle.
"""

from typing import Any

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Company


async def upsert_company_by_name(session: AsyncSession, payload: dict[str, Any]) -> Company:
    """Insert or fetch a Company. Ticker-first lookup when provided.

    payload keys (all optional except name):
      name:    legal or colloquial name
      ticker:  exchange ticker (ABBV, MRK, NVO, ...) — preferred identity
      sec_cik: SEC CIK — preferred over name when present
    """
    name = (payload.get("name") or "").strip()
    if not name:
        raise ValueError("company payload missing name")
    ticker = (payload.get("ticker") or "").strip() or None
    sec_cik = (payload.get("sec_cik") or "").strip() or None

    # Canonical lookups first — ticker, then CIK. Fall back to name.
    existing: Company | None = None
    if ticker:
        existing = await session.scalar(select(Company).where(Company.ticker == ticker))
    if existing is None and sec_cik:
        existing = await session.scalar(select(Company).where(Company.sec_cik == sec_cik))
    if existing is None:
        existing = await session.scalar(
            select(Company).where(func.lower(Company.name) == name.lower())
        )
        # Case: matched by name but lacks ticker; stamp ticker for future callers.
        if existing is not None and ticker and existing.ticker is None:
            existing.ticker = ticker
            await session.flush()

    if existing:
        return existing

    company = Company(name=name, ticker=ticker, sec_cik=sec_cik)
    session.add(company)
    await session.flush()
    return company


async def canonicalize_company_by_ticker(
    session: AsyncSession, ticker: str
) -> Company | None:
    """Return the Company row matching ticker, if any. Read-only."""
    if not ticker:
        return None
    return await session.scalar(
        select(Company).where(Company.ticker == ticker.strip())
    )
