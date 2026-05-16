"""Claim response schema."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ClaimRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    statement: str
    language: str
    claim_type: str
    evidence_basis: str | None
    confidence: str | None
    article_id: UUID | None
    entities_mentioned: list[str]
