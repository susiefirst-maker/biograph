"""SQLAlchemy models for the 11 Phase 0 entities (per ADR-0001).

Order of import matters for FK resolution: Company before Drug
(Drug.originator_id → Company), Drug/Article before Claim (Claim.article_id),
Drug before ClinicalTrial/RegulatoryDecision/Patent (FKs).
"""

from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin
from app.models._helpers import (
    ClaimType,
    CredibilityTier,
    DrugStatus,
    LessonType,
    PatentSourceRegister,
    TrialPhase,
    TrialStatus,
)

# Concrete entities (order: dependencies first)
from app.models.company import Company
from app.models.indication import Indication
from app.models.target import Target
from app.models.article import Article
from app.models.drug import Drug
from app.models.clinical_trial import ClinicalTrial
from app.models.regulatory_decision import RegulatoryDecision
from app.models.patent import Patent
from app.models.event import Event
from app.models.claim import Claim
from app.models.lesson import Lesson
from app.models.deal import Deal
from app.models.merge_conflict import MergeConflict

# Junction tables (must import so they register on Base.metadata)
from app.models import relationships  # noqa: F401

__all__ = [
    "Base",
    "BilingualNarrativeMixin",
    # Enums
    "ClaimType",
    "CredibilityTier",
    "DrugStatus",
    "LessonType",
    "PatentSourceRegister",
    "TrialPhase",
    "TrialStatus",
    # Entities
    "Company",
    "Indication",
    "Target",
    "Article",
    "Drug",
    "ClinicalTrial",
    "RegulatoryDecision",
    "Patent",
    "Event",
    "Claim",
    "Lesson",
    "Deal",
    "MergeConflict",
]
