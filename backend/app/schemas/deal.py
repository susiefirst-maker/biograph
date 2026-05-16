"""Deal response schema."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DealRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    deal_type: str
    headline: str
    announcement_date: date | None
    value_usd: int | None
    acquirer_id: UUID | None
    target_id: UUID | None
    description: str | None
    description_zh: str | None
    strategic_rationale: str | None
    strategic_rationale_zh: str | None
