"""Lesson response schema."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class LessonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    title: str
    title_zh: str | None
    lesson_type: str
    pattern: str | None
    pattern_zh: str | None
    key_evidence: list[dict]
    limitations: list[str]
    applicable_contexts: list[str]
    applicable_to_landscapes: list[str]
    human_reviewed: bool
