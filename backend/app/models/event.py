"""Event entity — atomic unit of historical narrative.

`triggered_by` is a self-FK enabling causal chains (design doc §5.2).
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


class Event(Base, BilingualNarrativeMixin):
    __tablename__ = "events"
    __narrative_fields__ = ["description"]

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    event_date: Mapped[date | None] = mapped_column(Date, index=True)
    headline: Mapped[str | None] = mapped_column(Text)
    significance: Mapped[str | None] = mapped_column(String(32))  # landmark/major/moderate/minor
    source_url: Mapped[str | None] = mapped_column(Text)

    # Bilingual narrative
    description: Mapped[str | None] = mapped_column(Text)
    description_zh: Mapped[str | None] = mapped_column(Text)
    description_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Causal chain — Event → Event self-FK (design doc §5.2)
    triggered_by: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("events.id"), index=True
    )

    # Polymorphic links to entities live in event_entity_link junction (relationships.py)

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
