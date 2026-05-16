"""Target response schema."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict


class TargetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    uniprot_id: str | None
    ensembl_id: str | None
    gene_symbol: str | None
    approved_name: str | None
    biotype: str | None
    biology_summary: str | None
    biology_summary_zh: str | None
    validation_history: str | None
    validation_history_zh: str | None
    competitive_landscape_summary: str | None
    competitive_landscape_summary_zh: str | None
    pathway_ids: list[str]
    go_molecular_function: list[str]
    go_biological_process: list[str]
    go_cellular_component: list[str]
