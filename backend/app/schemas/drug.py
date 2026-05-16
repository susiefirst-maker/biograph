"""Drug response schema — scalar fields only.

Relationships travel in the envelope's `related` block as chips, not
nested here. Deeper drill-downs are separate endpoints
(/api/drugs/{id}/timeline, /claims, /lessons) per ADR-0004.
"""

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class DrugRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    chembl_id: str | None
    drugbank_id: str | None

    generic_name: str
    brand_names: list[str]
    aliases: list[str]
    inn: str | None

    modality: str | None
    status: str
    max_phase: str | None
    first_approval_date: date | None

    mechanism_of_action: str | None
    mechanism_of_action_zh: str | None
    discovery_narrative: str | None
    discovery_narrative_zh: str | None

    revenue_peak_usd: int | None
    revenue_peak_year: int | None
    cumulative_revenue_usd: int | None
