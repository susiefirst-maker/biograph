"""Company entity — drug developer, marketer, or supporting org."""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


class Company(Base, BilingualNarrativeMixin):
    __tablename__ = "companies"
    __narrative_fields__ = ["origin_narrative", "strategic_summary"]

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifiers
    sec_cik: Mapped[str | None] = mapped_column(String(16), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    ticker: Mapped[str | None] = mapped_column(String(16), index=True)
    country: Mapped[str | None] = mapped_column(String(2))  # ISO 3166-1 alpha-2
    founded_date: Mapped[date | None] = mapped_column(Date)

    # Bilingual narratives
    origin_narrative: Mapped[str | None] = mapped_column(Text)
    origin_narrative_zh: Mapped[str | None] = mapped_column(Text)
    origin_narrative_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    strategic_summary: Mapped[str | None] = mapped_column(Text)
    strategic_summary_zh: Mapped[str | None] = mapped_column(Text)
    strategic_summary_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
