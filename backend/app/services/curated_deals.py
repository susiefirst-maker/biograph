"""Curated drug-deals loader — ADR-0012.

Applies data/curated/deals.yml. Resolves acquirer/target names to Company
rows (creating them if missing), persists Deal rows, links to Drug via
drug_deal_link.

Idempotency: Deal natural key is (headline, announcement_date). Upserts by
looking up existing match and updating in place.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Deal, Drug
from app.models.relationships import drug_deal_link
from app.services.company_service import upsert_company_by_name


CURATED_DIR = Path(__file__).resolve().parents[3] / "data" / "curated"
DEALS_FILE = CURATED_DIR / "deals.yml"


def _parse_date(raw: Any) -> date | None:
    if isinstance(raw, date):
        return raw
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date()
    except ValueError:
        return None


def load_drug_deals() -> list[dict[str, Any]]:
    if not DEALS_FILE.exists():
        return []
    doc = yaml.safe_load(DEALS_FILE.read_text()) or {}
    return doc.get("drugs") or []


async def apply_curated_deals(session: AsyncSession) -> int:
    """Returns number of (drug, deal) pairings applied."""
    entries = load_drug_deals()
    applied = 0

    for drug_entry in entries:
        chembl_id = drug_entry.get("chembl_id")
        deals = drug_entry.get("deals") or []
        if not chembl_id or not deals:
            continue

        drug = await session.scalar(select(Drug).where(Drug.chembl_id == chembl_id))
        if drug is None:
            continue

        for d in deals:
            headline = d.get("headline")
            ann_date = _parse_date(d.get("announcement_date"))
            if not headline:
                continue

            # Resolve acquirer / target companies. Ticker (when provided
            # in YAML) beats name — dedupes against SEC / CT.gov rows.
            acquirer = None
            if name := d.get("acquirer_name"):
                acquirer = await upsert_company_by_name(
                    session,
                    {"name": name, "ticker": d.get("acquirer_ticker")},
                )
            target_co = None
            if name := d.get("target_name"):
                target_co = await upsert_company_by_name(
                    session,
                    {"name": name, "ticker": d.get("target_ticker")},
                )

            # Natural key: (headline, announcement_date)
            existing = await session.scalar(
                select(Deal).where(
                    and_(
                        Deal.headline == headline,
                        Deal.announcement_date == ann_date,
                    )
                )
            )
            if existing is None:
                deal = Deal(
                    deal_type=d.get("deal_type", "acquisition"),
                    headline=headline,
                    announcement_date=ann_date,
                    value_usd=d.get("value_usd"),
                    acquirer_id=acquirer.id if acquirer else None,
                    target_id=target_co.id if target_co else None,
                    description=d.get("description"),
                    description_source_refs=d.get("source_refs") or [],
                    strategic_rationale=d.get("strategic_rationale"),
                    strategic_rationale_source_refs=d.get("source_refs") or [],
                    field_provenance={
                        "_curated_source": "data/curated/deals.yml",
                    },
                )
                session.add(deal)
                await session.flush()
                deal_id = deal.id
            else:
                # Update mutable fields — including FK re-stamping so a
                # re-run after ticker hints land in the YAML fixes stale
                # acquirer/target pointers (D-015).
                existing.value_usd = d.get("value_usd", existing.value_usd)
                existing.description = d.get("description") or existing.description
                existing.strategic_rationale = (
                    d.get("strategic_rationale") or existing.strategic_rationale
                )
                if acquirer:
                    existing.acquirer_id = acquirer.id
                if target_co:
                    existing.target_id = target_co.id
                deal_id = existing.id

            # Link drug ↔ deal (idempotent via ON CONFLICT)
            from sqlalchemy.dialects.postgresql import insert as pg_insert

            stmt = pg_insert(drug_deal_link).values(
                {"drug_id": drug.id, "deal_id": deal_id, "role": d.get("role", "included")}
            )
            stmt = stmt.on_conflict_do_nothing(index_elements=["drug_id", "deal_id"])
            await session.execute(stmt)
            applied += 1

    await session.flush()
    return applied
