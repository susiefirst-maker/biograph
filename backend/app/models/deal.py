"""Deal entity — business transactions (M&A, licensing, spinoffs).

Promoted from deferred (ADR-0001) to Phase 1 shipped per ADR-0012.
Bilingual: description + strategic_rationale per entity_inventory.md.
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


class Deal(Base, BilingualNarrativeMixin):
    __tablename__ = "deals"
    __narrative_fields__ = ["description", "strategic_rationale"]

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Classification + human-facing summary
    deal_type: Mapped[str] = mapped_column(String(32), nullable=False)  # acquisition / licensing / collaboration / spinoff / option
    headline: Mapped[str] = mapped_column(Text, nullable=False)
    announcement_date: Mapped[date | None] = mapped_column(Date, index=True)
    value_usd: Mapped[int | None] = mapped_column(BigInteger)

    # Participants (FKs to Company)
    acquirer_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), index=True
    )
    target_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), index=True
    )

    # Bilingual narratives (BilingualNarrativeMixin invariant, ADR-0006)
    description: Mapped[str | None] = mapped_column(Text)
    description_zh: Mapped[str | None] = mapped_column(Text)
    description_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    strategic_rationale: Mapped[str | None] = mapped_column(Text)
    strategic_rationale_zh: Mapped[str | None] = mapped_column(Text)
    strategic_rationale_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
