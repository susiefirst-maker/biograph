"""Company response schema."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class CompanyRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sec_cik: str | None
    name: str
    ticker: str | None
    country: str | None
    founded_date: date | None
    origin_narrative: str | None
    origin_narrative_zh: str | None
    strategic_summary: str | None
    strategic_summary_zh: str | None
