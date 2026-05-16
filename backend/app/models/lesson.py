"""Lesson entity — generalizable insight derived from one or more cases.

Bilingual per ADR-0006 (system-compiled, both languages valid).
`applicable_to_landscapes` is a list of slug strings per Q9=A / ADR-0010.
"""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Enum, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models._helpers import LessonType
from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


class Lesson(Base, BilingualNarrativeMixin):
    __tablename__ = "lessons"
    __narrative_fields__ = ["pattern"]

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    title: Mapped[str] = mapped_column(String(256), nullable=False)
    title_zh: Mapped[str | None] = mapped_column(String(256))

    lesson_type: Mapped[LessonType] = mapped_column(
        Enum(
            LessonType,
            name="lesson_type_kind",
            native_enum=True,
            values_callable=lambda e: [x.value for x in e],
        ),
        nullable=False,
    )

    # Bilingual narrative (the pattern itself is the lesson)
    pattern: Mapped[str | None] = mapped_column(Text)
    pattern_zh: Mapped[str | None] = mapped_column(Text)
    pattern_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Structured supporting fields (NOT bilingual — these are facts/lists)
    key_evidence: Mapped[list[dict]] = mapped_column(JSONB, default=list)
    limitations: Mapped[list[str]] = mapped_column(JSONB, default=list)
    applicable_contexts: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Landscape applicability (Q9=A / ADR-0010 — slug list)
    applicable_to_landscapes: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Editorial control
    human_reviewed: Mapped[bool] = mapped_column(default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(64))
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Polymorphic entity links live in entity_lesson_link junction (relationships.py)

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
