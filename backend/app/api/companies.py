"""Company detail route — GET /api/companies/{id}.

Related drugs use Drug.originator_id FK (no reverse relation on Company).
"""

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._deps import db, sources_from_provenance
from app.models import Company, Deal, Drug
from app.schemas.company import CompanyRead
from app.schemas.deal import DealRead
from app.schemas.drug import DrugRead
from app.schemas.envelope import (
    EntityEnvelope,
    EntityMeta,
    ErrorBody,
    ErrorEnvelope,
    ListEnvelope,
    ListMeta,
)

router = APIRouter(prefix="/api/companies", tags=["companies"])


@router.get(
    "/{company_id}",
    response_model=EntityEnvelope[CompanyRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_company(
    company_id: UUID, session: AsyncSession = Depends(db)
) -> EntityEnvelope[CompanyRead]:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="ENTITY_NOT_FOUND",
                message=f"Company with id={company_id} not found",
            ).model_dump(),
        )

    drugs_stmt = select(Drug).where(Drug.originator_id == company_id)
    drugs = (await session.scalars(drugs_stmt)).all()

    return EntityEnvelope[CompanyRead](
        data=CompanyRead.model_validate(company),
        meta=EntityMeta(
            entity_type="company",
            version=company.version,
            last_verified_at=company.last_verified_at,
            sources=sources_from_provenance(company.field_provenance),
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


async def _ensure_company(session: AsyncSession, company_id: UUID) -> Company:
    company = await session.get(Company, company_id)
    if company is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="ENTITY_NOT_FOUND",
                message=f"Company with id={company_id} not found",
            ).model_dump(),
        )
    return company


@router.get(
    "/{company_id}/pipeline",
    response_model=ListEnvelope[DrugRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_company_pipeline(
    company_id: UUID, session: AsyncSession = Depends(db)
) -> ListEnvelope[DrugRead]:
    await _ensure_company(session, company_id)
    stmt = select(Drug).where(Drug.originator_id == company_id).order_by(Drug.generic_name)
    drugs = (await session.scalars(stmt)).all()
    return ListEnvelope[DrugRead](
        data=[DrugRead.model_validate(d) for d in drugs],
        meta=ListMeta(count=len(drugs), entity_type="drug"),
    )


@router.get(
    "/{company_id}/deals",
    response_model=ListEnvelope[DealRead],
    responses={404: {"model": ErrorEnvelope}},
)
async def get_company_deals(
    company_id: UUID, session: AsyncSession = Depends(db)
) -> ListEnvelope[DealRead]:
    await _ensure_company(session, company_id)
    stmt = (
        select(Deal)
        .where(or_(Deal.acquirer_id == company_id, Deal.target_id == company_id))
        .order_by(Deal.announcement_date.desc())
    )
    deals = (await session.scalars(stmt)).all()
    return ListEnvelope[DealRead](
        data=[DealRead.model_validate(d) for d in deals],
        meta=ListMeta(count=len(deals), entity_type="deal"),
    )
