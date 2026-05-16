"""Indication entity — disease/condition for which drugs are developed."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


class Indication(Base, BilingualNarrativeMixin):
    __tablename__ = "indications"
    __narrative_fields__ = ["treatment_landscape_summary"]

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifiers
    efo_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    mesh_id: Mapped[str | None] = mapped_column(String(32), index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    name_zh: Mapped[str | None] = mapped_column(String(256))
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Bilingual narrative
    treatment_landscape_summary: Mapped[str | None] = mapped_column(Text)
    treatment_landscape_summary_zh: Mapped[str | None] = mapped_column(Text)
    treatment_landscape_summary_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
