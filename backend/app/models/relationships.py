"""Junction tables for entity relationships.

Two patterns:
  1. Type-specific many-to-many (drug_target_link, drug_indication_link, etc.)
     — used when both sides are known concrete types and the join is hot.
  2. Polymorphic (entity_claim_link, entity_lesson_link, event_entity_link)
     — used when one side may be any entity. Composite key
     (entity_type VARCHAR, entity_id UUID).

Single-FK relationships (ClinicalTrial.drug_id, Patent.drug_id, etc.) live
on the entity itself, not here.

The `entity_relationships` PostgreSQL VIEW (ADR-0002) is created via raw SQL
in the alembic migration; it reads from these tables.
"""

from sqlalchemy import Column, ForeignKey, String, Table
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from app.models.base import Base

# Type-specific junctions ────────────────────────────────────────────────────

drug_target_link = Table(
    "drug_target_link",
    Base.metadata,
    Column("drug_id", PG_UUID(as_uuid=True), ForeignKey("drugs.id", ondelete="CASCADE"), primary_key=True),
    Column("target_id", PG_UUID(as_uuid=True), ForeignKey("targets.id", ondelete="CASCADE"), primary_key=True),
    Column("action_type", String(64)),  # inhibitor, agonist, antagonist, ...
)

drug_indication_link = Table(
    "drug_indication_link",
    Base.metadata,
    Column("drug_id", PG_UUID(as_uuid=True), ForeignKey("drugs.id", ondelete="CASCADE"), primary_key=True),
    Column("indication_id", PG_UUID(as_uuid=True), ForeignKey("indications.id", ondelete="CASCADE"), primary_key=True),
    Column("max_phase", String(32)),
    Column("status", String(32)),  # approved, investigational, withdrawn
)

target_indication_link = Table(
    "target_indication_link",
    Base.metadata,
    Column("target_id", PG_UUID(as_uuid=True), ForeignKey("targets.id", ondelete="CASCADE"), primary_key=True),
    Column("indication_id", PG_UUID(as_uuid=True), ForeignKey("indications.id", ondelete="CASCADE"), primary_key=True),
    Column("association_score", String(16)),  # Open Targets score, stored as string for precision
)

# ADR-0012: Deal entity shipped Phase 1. Many-to-many — a deal can cover
# multiple drugs (bundled acquisitions) and a drug can be in multiple deals.
drug_deal_link = Table(
    "drug_deal_link",
    Base.metadata,
    Column("drug_id", PG_UUID(as_uuid=True), ForeignKey("drugs.id", ondelete="CASCADE"), primary_key=True),
    Column("deal_id", PG_UUID(as_uuid=True), ForeignKey("deals.id", ondelete="CASCADE"), primary_key=True),
    Column("role", String(32)),  # "included" / "flagship_asset" / "collateral"
)

# Polymorphic junctions ─────────────────────────────────────────────────────
# (entity_type, entity_id) composite — entity_type is one of:
#   drug, target, company, indication, clinical_trial, regulatory_decision,
#   patent, event (the 8 ship-now entities that can carry claims/lessons).

entity_claim_link = Table(
    "entity_claim_link",
    Base.metadata,
    Column("claim_id", PG_UUID(as_uuid=True), ForeignKey("claims.id", ondelete="CASCADE"), primary_key=True),
    Column("entity_type", String(32), primary_key=True),
    Column("entity_id", PG_UUID(as_uuid=True), primary_key=True),
)

entity_lesson_link = Table(
    "entity_lesson_link",
    Base.metadata,
    Column("lesson_id", PG_UUID(as_uuid=True), ForeignKey("lessons.id", ondelete="CASCADE"), primary_key=True),
    Column("entity_type", String(32), primary_key=True),
    Column("entity_id", PG_UUID(as_uuid=True), primary_key=True),
)

event_entity_link = Table(
    "event_entity_link",
    Base.metadata,
    Column("event_id", PG_UUID(as_uuid=True), ForeignKey("events.id", ondelete="CASCADE"), primary_key=True),
    Column("entity_type", String(32), primary_key=True),
    Column("entity_id", PG_UUID(as_uuid=True), primary_key=True),
    Column("role", String(64)),  # actor, subject, beneficiary, ...
)

__all__ = [
    "drug_target_link",
    "drug_indication_link",
    "target_indication_link",
    "drug_deal_link",
    "entity_claim_link",
    "entity_lesson_link",
    "event_entity_link",
]
