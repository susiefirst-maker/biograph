"""ClinicalTrial entity — registered clinical study from ClinicalTrials.gov."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


class ClinicalTrial(Base, BilingualNarrativeMixin):
    __tablename__ = "clinical_trials"
    __narrative_fields__ = ["results_summary"]

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifiers
    nct_id: Mapped[str] = mapped_column(String(16), unique=True, nullable=False, index=True)

    # Core fields
    title: Mapped[str | None] = mapped_column(Text)
    phase: Mapped[str | None] = mapped_column(String(32))
    status: Mapped[str | None] = mapped_column(String(64))
    enrollment: Mapped[int | None] = mapped_column(Integer)
    start_date: Mapped[date | None] = mapped_column(Date)
    completion_date: Mapped[date | None] = mapped_column(Date)

    # Per-trial outcomes (JSONB for flexibility — schemas vary)
    primary_outcomes: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    secondary_outcomes: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    conditions: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Drug + sponsor (denormalized FKs; multi-drug trials use junction Phase 1+)
    drug_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("drugs.id"), index=True
    )
    sponsor_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), index=True
    )

    # Bilingual narrative
    results_summary: Mapped[str | None] = mapped_column(Text)
    results_summary_zh: Mapped[str | None] = mapped_column(Text)
    results_summary_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Reverse relationship — Drug.trials back-populates from here (Phase 1 Day 1).
    drug: Mapped["Drug | None"] = relationship("Drug", back_populates="trials")
