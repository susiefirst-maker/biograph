"""Claim entity — structured assertion extracted from one or more sources.

Single-language per ADR-0006 (claims extract from single-language articles;
translating fabricates authorship).
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models._helpers import ClaimType
from app.models.base import Base


class Claim(Base):
    __tablename__ = "claims"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Statement (single language; the source article's language is authoritative)
    statement: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(String(8), nullable=False, default="en")

    # Epistemic typing
    claim_type: Mapped[ClaimType] = mapped_column(
        Enum(
            ClaimType,
            name="claim_type_kind",
            native_enum=True,
            values_callable=lambda e: [x.value for x in e],
        ),
        nullable=False,
    )
    evidence_basis: Mapped[str | None] = mapped_column(Text)
    confidence: Mapped[str | None] = mapped_column(String(16))  # high / medium / low

    # Source article
    article_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("articles.id"), index=True
    )

    # Entities mentioned (denormalized for quick filtering before full graph join)
    entities_mentioned: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Polymorphic entity links live in entity_claim_link junction (relationships.py)

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
