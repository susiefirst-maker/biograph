"""Target detail route — GET /api/targets/{id}.

Related drugs come from the drug_target_link junction (no reverse
relation on Target) — queried explicitly rather than lazy-loaded.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._deps import db, sources_from_provenance
from app.models import Drug, Target
from app.models.relationships import drug_target_link
from app.schemas.drug import DrugRead
from app.schemas.envelope import (
    EntityEnvelope,
    EntityMeta,
    ErrorBody,
    ErrorEnvelope,
    ListEnvelope,
    ListMeta,
)
from app.schemas.target import TargetRead

router = APIRouter(prefix="/api/targets", tags=["targets"])


@router.get(
    "/{target_id}",
    response_model=EntityEnvelope[TargetRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_target(
    target_id: UUID, session: AsyncSession = Depends(db)
) -> EntityEnvelope[TargetRead]:
    target = await session.get(Target, target_id)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="ENTITY_NOT_FOUND",
                message=f"Target with id={target_id} not found",
            ).model_dump(),
        )

    drugs_stmt = (
        select(Drug)
        .join(drug_target_link, drug_target_link.c.drug_id == Drug.id)
        .where(drug_target_link.c.target_id == target_id)
    )
    drugs = (await session.scalars(drugs_stmt)).all()

    return EntityEnvelope[TargetRead](
        data=TargetRead.model_validate(target),
        meta=EntityMeta(
            entity_type="target",
            version=target.version,
            last_verified_at=target.last_verified_at,
            sources=sources_from_provenance(target.field_provenance),
        ),
        related={
            "drugs": [
                {
                    "id": str(d.id),
                    "generic_name": d.generic_name,
                    "modality": d.modality,
                    "link": f"/api/drugs/{d.id}",
                }
                for d in drugs
            ],
        },
    )


@router.get(
    "/{target_id}/drugs",
    response_model=ListEnvelope[DrugRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_target_drugs(
    target_id: UUID, session: AsyncSession = Depends(db)
) -> ListEnvelope[DrugRead]:
    target = await session.get(Target, target_id)
    if target is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="ENTITY_NOT_FOUND",
                message=f"Target with id={target_id} not found",
            ).model_dump(),
        )
    stmt = (
        select(Drug)
        .join(drug_target_link, drug_target_link.c.drug_id == Drug.id)
        .where(drug_target_link.c.target_id == target_id)
        .order_by(Drug.generic_name)
    )
    drugs = (await session.scalars(stmt)).all()
    return ListEnvelope[DrugRead](
        data=[DrugRead.model_validate(d) for d in drugs],
        meta=ListMeta(count=len(drugs), entity_type="drug"),
    )
