"""Patent entity — IP protection. Single table + source_register enum (ADR-0005)."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models._helpers import PatentSourceRegister
from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


class Patent(Base, BilingualNarrativeMixin):
    __tablename__ = "patents"
    __narrative_fields__ = ["litigation_history"]

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Universal patent fields
    patent_number: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    title: Mapped[str | None] = mapped_column(Text)
    filing_date: Mapped[date | None] = mapped_column(Date)
    expiry_date: Mapped[date | None] = mapped_column(Date, index=True)

    # Source discriminator (ADR-0005)
    source_register: Mapped[PatentSourceRegister] = mapped_column(
        Enum(
            PatentSourceRegister,
            name="patent_source_register",
            native_enum=True,
            values_callable=lambda e: [x.value for x in e],
        ),
        nullable=False,
    )

    # Orange Book fields (nullable when source_register != orange_book)
    nda_number: Mapped[str | None] = mapped_column(String(32))
    patent_linkage_type: Mapped[str | None] = mapped_column(String(64))

    # Purple Book fields (nullable when source_register != purple_book)
    bla_number: Mapped[str | None] = mapped_column(String(32))
    reference_product_exclusivity_end: Mapped[date | None] = mapped_column(Date)

    # USPTO fields
    uspto_application_number: Mapped[str | None] = mapped_column(String(32))

    # Bilingual narrative
    litigation_history: Mapped[str | None] = mapped_column(Text)
    litigation_history_zh: Mapped[str | None] = mapped_column(Text)
    litigation_history_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

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

    # Reverse — Drug.patents back-populates here (Phase 1 Day 4).
    drug: Mapped["Drug | None"] = relationship("Drug", back_populates="patents")
