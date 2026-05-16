"""ClinicalTrial persistence — idempotent upserts keyed by nct_id.

Phase 1 Day 1: single-drug FK only (Drug.trials → ClinicalTrial.drug_id).
Multi-drug trials (e.g., combo regimens) need a junction table — deferred.

Phase 1 Day 6: switched from check-then-insert to Postgres INSERT ... ON
CONFLICT (nct_id) DO UPDATE. The old path races under concurrent batch
ingest when the same NCT appears in multiple drugs' trial lists
(e.g., "Aliskiren vs Atenolol" belongs to both drugs).
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import ClinicalTrial, Drug
from app.services.company_service import upsert_company_by_name


async def upsert_clinical_trials_from_ctgov(
    session: AsyncSession,
    drug_id: UUID | None,
    normalized: dict[str, Any],
) -> list[ClinicalTrial]:
    """Persist a list of normalized CT.gov trials. Links each to drug_id and to a Company by sponsor name.

    Race-safe under concurrent batch ingest via ON CONFLICT (nct_id) DO UPDATE.
    """
    # 1. Upsert sponsor companies by name first (Company.name isn't unique;
    #    race-safe because upsert_company_by_name re-queries inside each call).
    name_to_id: dict[str, UUID] = {}
    for comp_payload in normalized.get("companies", []):
        company = await upsert_company_by_name(session, comp_payload)
        name_to_id[(comp_payload["name"] or "").lower()] = company.id

    # 2. Bulk upsert trials using ON CONFLICT (nct_id). drug_id and sponsor_id
    #    preserved when already set (COALESCE semantics).
    trials_payload = normalized.get("trials", [])
    if not trials_payload:
        return []

    # Dedup by nct_id before upsert — PG ON CONFLICT can't handle
    # intra-batch duplicates (CardinalityViolation).
    by_key: dict[str, dict] = {}
    for t_payload in trials_payload:
        sponsor_id = name_to_id.get((t_payload.get("sponsor_name") or "").lower())
        by_key[t_payload["nct_id"]] = {
            "nct_id": t_payload["nct_id"],
            "title": t_payload.get("title"),
            "phase": t_payload.get("phase"),
            "status": t_payload.get("status"),
            "enrollment": t_payload.get("enrollment"),
            "start_date": t_payload.get("start_date"),
            "completion_date": t_payload.get("completion_date"),
            "conditions": t_payload.get("conditions") or [],
            "primary_outcomes": t_payload.get("primary_outcomes") or [],
            "secondary_outcomes": t_payload.get("secondary_outcomes") or [],
            "drug_id": drug_id,
            "sponsor_id": sponsor_id,
        }
    rows = list(by_key.values())

    stmt = pg_insert(ClinicalTrial).values(rows)
    # On conflict: update non-null incoming fields, preserve existing drug_id
    # and sponsor_id where already set (a cross-drug trial hit from another
    # drug's ingest is informational, not a full claim over the trial).
    update_cols = {
        "title": stmt.excluded.title,
        "phase": stmt.excluded.phase,
        "status": stmt.excluded.status,
        "enrollment": stmt.excluded.enrollment,
        "start_date": stmt.excluded.start_date,
        "completion_date": stmt.excluded.completion_date,
        "conditions": stmt.excluded.conditions,
        "primary_outcomes": stmt.excluded.primary_outcomes,
        "secondary_outcomes": stmt.excluded.secondary_outcomes,
        # Only overwrite drug_id / sponsor_id when the existing row is NULL.
        "drug_id": _coalesce_existing(ClinicalTrial.drug_id, stmt.excluded.drug_id),
        "sponsor_id": _coalesce_existing(ClinicalTrial.sponsor_id, stmt.excluded.sponsor_id),
    }
    stmt = stmt.on_conflict_do_update(index_elements=["nct_id"], set_=update_cols)
    await session.execute(stmt)
    await session.flush()

    # Re-load the upserted rows for caller convenience
    nct_ids = [r["nct_id"] for r in rows]
    result = await session.execute(select(ClinicalTrial).where(ClinicalTrial.nct_id.in_(nct_ids)))
    return list(result.scalars())


def _coalesce_existing(existing_col, incoming_col):
    """SQL COALESCE(existing, incoming) — keeps existing value if non-null."""
    from sqlalchemy import func

    return func.coalesce(existing_col, incoming_col)


async def find_drug_for_intervention(session: AsyncSession, intervention_name: str) -> Drug | None:
    """Return the Drug whose generic_name matches the intervention (lowercase exact)."""
    return await session.scalar(
        select(Drug).where(Drug.generic_name == intervention_name.lower())
    )


async def find_drug_for_intervention(session: AsyncSession, intervention_name: str) -> Drug | None:
    """Return the Drug whose generic_name matches the intervention (lowercase exact)."""
    return await session.scalar(
        select(Drug).where(Drug.generic_name == intervention_name.lower())
    )
