"""Drug entity — central object of BioGraph.

Phase 0: minimum viable fields. Phase 1 ingesters add per-source detail
(SMILES, InChI, ATC, etc.) without schema migration (use JSONB).
"""

from datetime import date, datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, Date, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


class Drug(Base, BilingualNarrativeMixin):
    __tablename__ = "drugs"
    __narrative_fields__ = ["mechanism_of_action", "discovery_narrative"]

    id: Mapped[UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid4)

    # Identifiers
    drugbank_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)
    chembl_id: Mapped[str | None] = mapped_column(String(32), unique=True, index=True)

    # Names
    generic_name: Mapped[str] = mapped_column(String(256), nullable=False, index=True)
    brand_names: Mapped[list[str]] = mapped_column(JSONB, default=list)  # ["Humira", "修美乐"]
    aliases: Mapped[list[str]] = mapped_column(JSONB, default=list)
    inn: Mapped[str | None] = mapped_column(String(256))

    # Modality + status
    modality: Mapped[str | None] = mapped_column(String(64))  # FK→Modality deferred (ADR-0001)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="investigational")
    max_phase: Mapped[str | None] = mapped_column(String(32))
    first_approval_date: Mapped[date | None] = mapped_column(Date)

    # Bilingual narratives (per BilingualNarrativeMixin invariant)
    mechanism_of_action: Mapped[str | None] = mapped_column(Text)
    mechanism_of_action_zh: Mapped[str | None] = mapped_column(Text)
    mechanism_of_action_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    discovery_narrative: Mapped[str | None] = mapped_column(Text)
    discovery_narrative_zh: Mapped[str | None] = mapped_column(Text)
    discovery_narrative_source_refs: Mapped[list[str]] = mapped_column(JSONB, default=list)

    # Commercial (sourced from SEC EDGAR per ADR-0007 precedence)
    revenue_peak_usd: Mapped[int | None] = mapped_column(BigInteger)
    revenue_peak_year: Mapped[int | None] = mapped_column(Integer)
    cumulative_revenue_usd: Mapped[int | None] = mapped_column(BigInteger)

    # Originator (FK to Company)
    originator_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("companies.id"), index=True
    )
    # P2-D3: biosimilar_of (Drug ↔ Drug self-reference, m:1).
    # A biosimilar points at its reference biologic; nullable for originators
    # and small molecules.
    biosimilar_of_id: Mapped[UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("drugs.id"), index=True
    )

    # Cross-source provenance per field (ADR-0007)
    field_provenance: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
    version: Mapped[int] = mapped_column(Integer, default=1)
    last_verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    # Type-specific many-to-many relationships (Day 4+).
    # Polymorphic Claim/Lesson junctions stay in relationships.py and are
    # queried via services, not via ORM relationships — see Day 3 commit.
    targets: Mapped[list["Target"]] = relationship(
        "Target", secondary="drug_target_link", lazy="selectin"
    )
    indications: Mapped[list["Indication"]] = relationship(
        "Indication", secondary="drug_indication_link", lazy="selectin"
    )
    # Single-FK reverse: ClinicalTrial.drug_id (Phase 1 Day 1).
    # Multi-drug trials (e.g., Keytruda+chemo) need a junction — Phase 1+.
    trials: Mapped[list["ClinicalTrial"]] = relationship(
        "ClinicalTrial", back_populates="drug", lazy="selectin"
    )
    # Phase 1 Day 2: RegulatoryDecision.drug_id reverse.
    regulatory_decisions: Mapped[list["RegulatoryDecision"]] = relationship(
        "RegulatoryDecision", back_populates="drug", lazy="selectin"
    )
    # Phase 1 Day 4: Patent.drug_id reverse (curated + future USPTO-driven).
    patents: Mapped[list["Patent"]] = relationship(
        "Patent", back_populates="drug", lazy="selectin"
    )
    # Phase 1 Day 8 (ADR-0012): Deal promoted to shipped.
    deals: Mapped[list["Deal"]] = relationship(
        "Deal", secondary="drug_deal_link", lazy="selectin"
    )
    # Phase 1 Day 8 (C): events via polymorphic event_entity_link filtered by
    # entity_type='drug'. viewonly=True — writes go through event_entity_link
    # directly (curated_events loader) since the junction carries entity_type.
    events: Mapped[list["Event"]] = relationship(
        "Event",
        secondary="event_entity_link",
        primaryjoin=(
            "and_(Drug.id == event_entity_link.c.entity_id, "
            "event_entity_link.c.entity_type == 'drug')"
        ),
        secondaryjoin="Event.id == event_entity_link.c.event_id",
        viewonly=True,
        lazy="selectin",
    )
    # Phase 2 P2-D2: claims via polymorphic entity_claim_link. Same viewonly
    # pattern as events. Writes go through entity_claim_link (curated_claims
    # loader or future Mode 2 LLM extraction).
    claims: Mapped[list["Claim"]] = relationship(
        "Claim",
        secondary="entity_claim_link",
        primaryjoin=(
            "and_(Drug.id == entity_claim_link.c.entity_id, "
            "entity_claim_link.c.entity_type == 'drug')"
        ),
        secondaryjoin="Claim.id == entity_claim_link.c.claim_id",
        viewonly=True,
        lazy="selectin",
    )
    # Phase 2 P2-D3: lessons via polymorphic entity_lesson_link, filtered by
    # entity_type='drug'. Same pattern as events and claims.
    lessons: Mapped[list["Lesson"]] = relationship(
        "Lesson",
        secondary="entity_lesson_link",
        primaryjoin=(
            "and_(Drug.id == entity_lesson_link.c.entity_id, "
            "entity_lesson_link.c.entity_type == 'drug')"
        ),
        secondaryjoin="Lesson.id == entity_lesson_link.c.lesson_id",
        viewonly=True,
        lazy="selectin",
    )
    # P2-D3: biosimilars — reverse of biosimilar_of_id.
    biosimilars: Mapped[list["Drug"]] = relationship(
        "Drug",
        foreign_keys=[biosimilar_of_id],
        remote_side="Drug.biosimilar_of_id",
        primaryjoin="Drug.id == Drug.biosimilar_of_id",
        viewonly=True,
        lazy="selectin",
    )
