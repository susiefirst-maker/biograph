"""RegulatoryDecision persistence — idempotent on (application_number, submission_number).

Day 7 (Phase 1): race-safe via ON CONFLICT on the composite unique index.
Before Day 7 there was no unique constraint and concurrent batch ingest
silently produced duplicate rows; Day 7 migration dedups + adds the index.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import and_, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RegulatoryDecision
from app.services.company_service import upsert_company_by_name


async def upsert_regulatory_decisions_from_fda(
    session: AsyncSession,
    drug_id: UUID | None,
    normalized: dict[str, Any],
    link_only_originator: bool = True,
) -> list[RegulatoryDecision]:
    """Race-safe upsert via ON CONFLICT (application_number, submission_number)."""
    for comp_payload in normalized.get("companies", []):
        await upsert_company_by_name(session, comp_payload)

    decisions_payload = normalized.get("decisions", [])
    if not decisions_payload:
        return []

    # Dedup by (application_number, submission_number) before upsert.
    # openFDA can list the same submission across multiple results entries;
    # PG ON CONFLICT can't handle intra-batch duplicates (CardinalityViolation).
    by_key: dict[tuple, dict] = {}
    for payload in decisions_payload:
        key = (payload["application_number"], payload.get("submission_number"))
        link_drug = drug_id if (payload.get("_is_originator") or not link_only_originator) else None
        by_key[key] = {
            "application_number": payload["application_number"],
            "bla_number": payload.get("bla_number"),
            "nda_number": payload.get("nda_number"),
            "jurisdiction": payload["jurisdiction"],
            "action_type": payload["action_type"],
            "decision_date": payload.get("decision_date"),
            "notes": payload.get("notes"),
            "review_documents": payload.get("review_documents") or [],
            "submission_number": payload.get("submission_number"),
            "submission_type": payload.get("submission_type"),
            "review_priority": payload.get("review_priority"),
            "drug_id": link_drug,
        }
    rows = list(by_key.values())

    stmt = pg_insert(RegulatoryDecision).values(rows)
    stmt = stmt.on_conflict_do_update(
        index_elements=["application_number", "submission_number"],
        set_={
            "action_type": stmt.excluded.action_type,
            "decision_date": stmt.excluded.decision_date,
            "notes": func.coalesce(stmt.excluded.notes, RegulatoryDecision.notes),
            "review_documents": stmt.excluded.review_documents,
            # Keep existing drug_id if already set (originator-link is monotonic)
            "drug_id": func.coalesce(RegulatoryDecision.drug_id, stmt.excluded.drug_id),
        },
    )
    await session.execute(stmt)
    await session.flush()

    # Re-load for caller
    keys = [(r["application_number"], r.get("submission_number")) for r in rows]
    result = await session.execute(
        select(RegulatoryDecision).where(
            RegulatoryDecision.application_number.in_([k[0] for k in keys])
        )
    )
    return list(result.scalars())
