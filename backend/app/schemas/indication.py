"""Indication response schema."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class IndicationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    efo_id: str | None
    mesh_id: str | None
    name: str
    name_zh: str | None
    aliases: list[str]
    treatment_landscape_summary: str | None
    treatment_landscape_summary_zh: str | None
