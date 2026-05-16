"""RegulatoryDecision entity — approval, rejection, label change, designation.

NOT bilingual per ADR-0006 (no narrative fields, only structured data).
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base


class RegulatoryDecision(Base):
    __tablename__ = "regulatory_decisions"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifiers
    bla_number: Mapped[str | None] = mapped_column(String(32), index=True)  # biologics
    nda_number: Mapped[str | None] = mapped_column(String(32), index=True)  # small molecules
    application_number: Mapped[str | None] = mapped_column(String(64), index=True)  # generic catch-all

    # Decision details
    jurisdiction: Mapped[str] = mapped_column(String(8), nullable=False)  # FDA, EMA, PMDA, NMPA
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)  # approval, label_change, withdrawal
    decision_date: Mapped[date | None] = mapped_column(Date, index=True)
    indication_text: Mapped[str | None] = mapped_column(Text)
    notes: Mapped[str | None] = mapped_column(Text)
    review_documents: Mapped[list[str]] = mapped_column(JSONB, default=list)  # URLs

    # Submission-level details (openFDA: submissions[] per application).
    # Natural dedup key: (application_number, submission_number).
    submission_number: Mapped[str | None] = mapped_column(String(16))
    submission_type: Mapped[str | None] = mapped_column(String(16))  # ORIG / SUPPL
    review_priority: Mapped[str | None] = mapped_column(String(16))  # STANDARD / PRIORITY

    # FK to drug
    drug_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("drugs.id"), index=True
    )

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)

    # Reverse relationship — Drug.regulatory_decisions back-populates here.
    drug: Mapped["Drug | None"] = relationship("Drug", back_populates="regulatory_decisions")
