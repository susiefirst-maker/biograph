"""Event response schema — timeline rendering."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class EventRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    event_type: str
    event_date: date | None
    headline: str | None
    significance: str | None
    description: str | None
    description_zh: str | None
    source_url: str | None
    triggered_by: UUID | None
