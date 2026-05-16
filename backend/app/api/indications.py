"""Indication detail route — GET /api/indications/{id}.

Related drugs come from the drug_indication_link junction.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._deps import db, sources_from_provenance
from app.models import Drug, Indication
from app.models.relationships import drug_indication_link
from app.schemas.envelope import EntityEnvelope, EntityMeta, ErrorBody, ErrorEnvelope
from app.schemas.indication import IndicationRead

router = APIRouter(prefix="/api/indications", tags=["indications"])


@router.get(
    "/{indication_id}",
    response_model=EntityEnvelope[IndicationRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_indication(
    indication_id: UUID, session: AsyncSession = Depends(db)
) -> EntityEnvelope[IndicationRead]:
    indication = await session.get(Indication, indication_id)
    if indication is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="ENTITY_NOT_FOUND",
                message=f"Indication with id={indication_id} not found",
            ).model_dump(),
        )

    drugs_stmt = (
        select(Drug)
        .join(drug_indication_link, drug_indication_link.c.drug_id == Drug.id)
        .where(drug_indication_link.c.indication_id == indication_id)
    )
    drugs = (await session.scalars(drugs_stmt)).all()

    return EntityEnvelope[IndicationRead](
        data=IndicationRead.model_validate(indication),
        meta=EntityMeta(
            entity_type="indication",
            version=indication.version,
            last_verified_at=indication.last_verified_at,
            sources=sources_from_provenance(indication.field_provenance),
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
