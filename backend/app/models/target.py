"""Target entity — biological target (protein, gene, receptor)."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


class Target(Base, BilingualNarrativeMixin):
    __tablename__ = "targets"
    __narrative_fields__ = ["biology_summary", "validation_history", "competitive_landscape_summary"]

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifiers
    uniprot_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    ensembl_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    gene_symbol: Mapped[str | None] = mapped_column(String(64), index=True)
    approved_name: Mapped[str | None] = mapped_column(String(512))

    # Biotype (protein, ncRNA, etc.)
    biotype: Mapped[str | None] = mapped_column(String(64))

    # Bilingual narratives
    biology_summary: Mapped[str | None] = mapped_column(Text)
    biology_summary_zh: Mapped[str | None] = mapped_column(Text)
    biology_summary_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    validation_history: Mapped[str | None] = mapped_column(Text)
    validation_history_zh: Mapped[str | None] = mapped_column(Text)
    validation_history_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    competitive_landscape_summary: Mapped[str | None] = mapped_column(Text)
    competitive_landscape_summary_zh: Mapped[str | None] = mapped_column(Text)
    competitive_landscape_summary_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # PrimeKG-derived enrichment (per Day 2 audit, entity_inventory.md)
    pathway_ids: Mapped[list[str]] = mapped_column(JSONB, default=list)  # Reactome / KEGG IDs
    go_molecular_function: Mapped[list[str]] = mapped_column(JSONB, default=list)
    go_biological_process: Mapped[list[str]] = mapped_column(JSONB, default=list)
    go_cellular_component: Mapped[list[str]] = mapped_column(JSONB, default=list)

    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
