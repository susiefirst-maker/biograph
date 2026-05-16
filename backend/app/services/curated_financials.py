"""Curated drug financials loader — applies data/curated/drug_financials.yml
to Drug rows.

Why curated: SEC XBRL does not expose product-level revenue for most drugs.
Product figures ($20.7B Humira peak in 2021) are well-documented but live
in 10-K text, segment tables, or analyst databases. We curate them in
a versioned YAML with explicit source_refs.
"""

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Drug


CURATED_DIR = Path(__file__).resolve().parents[3] / "data" / "curated"
DRUG_FINANCIALS_FILE = CURATED_DIR / "drug_financials.yml"


def load_drug_financials() -> list[dict[str, Any]]:
    """Parse the curated YAML. Returns list of drug payloads."""
    if not DRUG_FINANCIALS_FILE.exists():
        return []
    doc = yaml.safe_load(DRUG_FINANCIALS_FILE.read_text()) or {}
    return doc.get("drugs") or []


async def apply_curated_financials(session: AsyncSession) -> int:
    """Apply every curated drug-financials entry; return count of updated rows."""
    entries = load_drug_financials()
    updated = 0

    for entry in entries:
        chembl_id = entry.get("chembl_id")
        if not chembl_id:
            continue
        drug = await session.scalar(select(Drug).where(Drug.chembl_id == chembl_id))
        if drug is None:
            # Skip — drug not yet ingested; applying is a no-op, not a failure.
            continue
        if (peak := entry.get("revenue_peak_usd")) is not None:
            drug.revenue_peak_usd = int(peak)
        if (year := entry.get("revenue_peak_year")) is not None:
            drug.revenue_peak_year = int(year)
        if (cum := entry.get("cumulative_revenue_usd")) is not None:
            drug.cumulative_revenue_usd = int(cum)

        refs = entry.get("source_refs") or []
        # Stamp provenance so ADR-0007 merge layer sees these weren't ingester output
        drug.field_provenance = {
            **(drug.field_provenance or {}),
            "revenue_peak_usd": "curated:drug_financials.yml",
            "revenue_peak_year": "curated:drug_financials.yml",
            "cumulative_revenue_usd": "curated:drug_financials.yml",
            "_curated_source_refs": refs,
        }
        updated += 1

    return updated
