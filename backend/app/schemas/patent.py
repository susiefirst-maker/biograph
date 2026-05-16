"""Patent response schema."""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PatentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, use_enum_values=True)

    id: UUID
    patent_number: str
    title: str | None
    filing_date: date | None
    expiry_date: date | None
    source_register: str
    nda_number: str | None
    bla_number: str | None
    uspto_application_number: str | None
    reference_product_exclusivity_end: date | None
    litigation_history: str | None
    litigation_history_zh: str | None
