"""RegulatoryDecision response schema."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class RegulatoryDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    jurisdiction: str
    action_type: str
    decision_date: date | None
    application_number: str | None
    bla_number: str | None
    nda_number: str | None
    submission_number: str | None
    submission_type: str | None
    review_priority: str | None
    indication_text: str | None
    notes: str | None
    review_documents: list[str]
