"""Drug detail route — GET /api/drugs/{id}.

Phase 3 Day 1: the first entity endpoint. Relationships are eagerly
loaded via `lazy="selectin"` on the Drug model, so a single `session.get`
populates targets/indications/trials/etc. without a separate round-trip.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api._deps import db, sources_from_provenance
from app.models import Drug
from app.models._helpers import PatentSourceRegister
from app.schemas.claim import ClaimRead
from app.schemas.drug import DrugRead
from app.schemas.envelope import (
    EntityEnvelope,
    EntityMeta,
    ErrorBody,
    ErrorEnvelope,
    ListEnvelope,
    ListMeta,
)
from app.schemas.event import EventRead
from app.schemas.lesson import LessonRead
from app.schemas.patent import PatentRead
from app.schemas.regulatory_decision import RegulatoryDecisionRead

router = APIRouter(prefix="/api/drugs", tags=["drugs"])


@router.get(
    "/{drug_id}",
    response_model=EntityEnvelope[DrugRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_drug(drug_id: UUID, session: AsyncSession = Depends(db)) -> EntityEnvelope[DrugRead]:
    stmt = (
        select(Drug)
        .where(Drug.id == drug_id)
        .options(
            selectinload(Drug.targets),
            selectinload(Drug.indications),
            selectinload(Drug.biosimilars),
        )
    )
    drug = await session.scalar(stmt)
    if drug is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="ENTITY_NOT_FOUND",
                message=f"Drug with id={drug_id} not found",
            ).model_dump(),
        )

    return EntityEnvelope[DrugRead](
        data=DrugRead.model_validate(drug),
        meta=EntityMeta(
            entity_type="drug",
            version=drug.version,
            last_verified_at=drug.last_verified_at,
            sources=sources_from_provenance(drug.field_provenance),
        ),
        related={
            "targets": [
                {
                    "id": str(t.id),
                    "gene_symbol": t.gene_symbol,
                    "approved_name": t.approved_name,
                    "link": f"/api/targets/{t.id}",
                }
                for t in drug.targets
            ],
            "indications": [
                {
                    "id": str(i.id),
                    "efo_id": i.efo_id,
                    "name": i.name,
                    "link": f"/api/indications/{i.id}",
                }
                for i in drug.indications
            ],
            "biosimilars": [
                {
                    "id": str(b.id),
                    "generic_name": b.generic_name,
                    "link": f"/api/drugs/{b.id}",
                }
                for b in drug.biosimilars
            ],
        },
    )


async def _load_drug_with(session: AsyncSession, drug_id: UUID, *rel) -> Drug:
    stmt = select(Drug).where(Drug.id == drug_id).options(*(selectinload(r) for r in rel))
    drug = await session.scalar(stmt)
    if drug is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="ENTITY_NOT_FOUND",
                message=f"Drug with id={drug_id} not found",
            ).model_dump(),
        )
    return drug


@router.get(
    "/{drug_id}/timeline",
    response_model=ListEnvelope[EventRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_drug_timeline(
    drug_id: UUID, session: AsyncSession = Depends(db)
) -> ListEnvelope[EventRead]:
    drug = await _load_drug_with(session, drug_id, Drug.events)
    events = sorted(
        drug.events,
        key=lambda e: (e.event_date is None, e.event_date),
    )
    return ListEnvelope[EventRead](
        data=[EventRead.model_validate(e) for e in events],
        meta=ListMeta(count=len(events), entity_type="event"),
    )


@router.get(
    "/{drug_id}/claims",
    response_model=ListEnvelope[ClaimRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_drug_claims(
    drug_id: UUID, session: AsyncSession = Depends(db)
) -> ListEnvelope[ClaimRead]:
    drug = await _load_drug_with(session, drug_id, Drug.claims)
    return ListEnvelope[ClaimRead](
        data=[ClaimRead.model_validate(c) for c in drug.claims],
        meta=ListMeta(count=len(drug.claims), entity_type="claim"),
    )


@router.get(
    "/{drug_id}/lessons",
    response_model=ListEnvelope[LessonRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_drug_lessons(
    drug_id: UUID, session: AsyncSession = Depends(db)
) -> ListEnvelope[LessonRead]:
    drug = await _load_drug_with(session, drug_id, Drug.lessons)
    # Human-reviewed first; within each group preserve insertion order.
    lessons = sorted(drug.lessons, key=lambda l: (not l.human_reviewed,))
    return ListEnvelope[LessonRead](
        data=[LessonRead.model_validate(l) for l in lessons],
        meta=ListMeta(count=len(lessons), entity_type="lesson"),
    )


@router.get(
    "/{drug_id}/patents",
    response_model=ListEnvelope[PatentRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_drug_patents(
    drug_id: UUID,
    register: PatentSourceRegister | None = Query(
        None,
        description="Filter to a single source_register (ADR-0005)",
    ),
    session: AsyncSession = Depends(db),
) -> ListEnvelope[PatentRead]:
    drug = await _load_drug_with(session, drug_id, Drug.patents)
    patents = drug.patents
    if register is not None:
        patents = [p for p in patents if p.source_register == register]
    # Expiry-date ascending; None (unknown expiry) last.
    patents = sorted(patents, key=lambda p: (p.expiry_date is None, p.expiry_date))
    return ListEnvelope[PatentRead](
        data=[PatentRead.model_validate(p) for p in patents],
        meta=ListMeta(count=len(patents), entity_type="patent"),
    )


@router.get(
    "/{drug_id}/regulatory-decisions",
    response_model=ListEnvelope[RegulatoryDecisionRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_drug_regulatory_decisions(
    drug_id: UUID,
    jurisdiction: str | None = Query(None, description="Filter by jurisdiction (FDA, EMA, ...)"),
    session: AsyncSession = Depends(db),
) -> ListEnvelope[RegulatoryDecisionRead]:
    drug = await _load_drug_with(session, drug_id, Drug.regulatory_decisions)
    decisions = drug.regulatory_decisions
    if jurisdiction is not None:
        decisions = [d for d in decisions if d.jurisdiction == jurisdiction]
    decisions = sorted(
        decisions, key=lambda d: (d.decision_date is None, d.decision_date)
    )
    return ListEnvelope[RegulatoryDecisionRead](
        data=[RegulatoryDecisionRead.model_validate(d) for d in decisions],
        meta=ListMeta(count=len(decisions), entity_type="regulatory_decision"),
    )
