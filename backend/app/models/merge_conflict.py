"""MergeConflict entity — ADR-0007 audit log for cross-source field conflicts."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class MergeConflict(Base):
    __tablename__ = "merge_conflicts"

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)
    entity_type: Mapped[str] = mapped_column(String(32), nullable=False)
    entity_id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), nullable=False)
    field_name: Mapped[str] = mapped_column(String(128), nullable=False)
    field_category: Mapped[str] = mapped_column(String(32), nullable=False)
    source_a: Mapped[str] = mapped_column(String(64), nullable=False)
    value_a: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB)
    source_b: Mapped[str] = mapped_column(String(64), nullable=False)
    value_b: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB)
    resolved_source: Mapped[str] = mapped_column(String(64), nullable=False)
    resolved_value: Mapped[dict | list | str | int | float | bool | None] = mapped_column(JSONB)
    resolution_reason: Mapped[str] = mapped_column(String(32), nullable=False)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    resolved_by: Mapped[str | None] = mapped_column(String(64))
