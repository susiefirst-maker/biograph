"""Curated drug-patents loader — applies data/curated/drug_patents.yml.

Idempotent: natural key is (patent_number, source_register). Per-run
matching skips existing rows and updates mutable fields (title, dates).

Phase 1 Day 4: seeds the Humira anchor patent (US6090382). Full patent
thicket (≥100 rows) requires PatentsView API key or pasted I-MAK list;
see drug_patents.yml module header.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Drug, Patent
from app.models._helpers import PatentSourceRegister


CURATED_DIR = Path(__file__).resolve().parents[3] / "data" / "curated"
DRUG_PATENTS_FILE = CURATED_DIR / "drug_patents.yml"


def _parse_date(raw: Any) -> date | None:
    if isinstance(raw, date):
        return raw
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date()
    except ValueError:
        return None


def load_drug_patents() -> list[dict[str, Any]]:
    if not DRUG_PATENTS_FILE.exists():
        return []
    doc = yaml.safe_load(DRUG_PATENTS_FILE.read_text()) or {}
    return doc.get("drugs") or []


async def apply_curated_patents(session: AsyncSession) -> int:
    """Apply every patent entry under every drug. Returns count of patent rows written/updated."""
    entries = load_drug_patents()
    applied = 0

    for drug_entry in entries:
        chembl_id = drug_entry.get("chembl_id")
        patents = drug_entry.get("patents") or []
        if not chembl_id or not patents:
            continue

        drug = await session.scalar(select(Drug).where(Drug.chembl_id == chembl_id))
        if drug is None:
            continue  # Drug not yet ingested; re-run after ingest.

        for p in patents:
            patent_number = p.get("patent_number")
            register_raw = p.get("source_register") or "uspto_manual"
            if not patent_number:
                continue

            try:
                source_register = PatentSourceRegister(register_raw.lower())
            except ValueError:
                continue  # Unknown register value — skip silently per ADR-0005

            existing = await session.scalar(
                select(Patent).where(
                    and_(
                        Patent.patent_number == patent_number,
                        Patent.source_register == source_register,
                    )
                )
            )
            if existing is None:
                patent = Patent(
                    patent_number=patent_number,
                    title=p.get("title"),
                    filing_date=_parse_date(p.get("filing_date")),
                    expiry_date=_parse_date(p.get("expiry_date")),
                    source_register=source_register,
                    drug_id=drug.id,
                    litigation_history=p.get("notes"),
                    litigation_history_source_refs=p.get("citations") or [],
                    field_provenance={
                        "patent_number": "curated:drug_patents.yml",
                        "_curated_citations": p.get("citations") or [],
                    },
                )
                session.add(patent)
            else:
                # Update mutable fields; preserve identity
                existing.title = p.get("title") or existing.title
                fd = _parse_date(p.get("filing_date"))
                ed = _parse_date(p.get("expiry_date"))
                if fd:
                    existing.filing_date = fd
                if ed:
                    existing.expiry_date = ed
                if drug.id and existing.drug_id is None:
                    existing.drug_id = drug.id
            applied += 1

    await session.flush()
    return applied
