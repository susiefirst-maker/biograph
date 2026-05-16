"""Shared enum types and column helpers used across entity models.

Enums are PostgreSQL ENUM types created at migration time. Naming convention:
table-or-domain prefix + suffix `_kind` for clarity in pgsql.
"""

from enum import StrEnum


class PatentSourceRegister(StrEnum):
    """ADR-0005: which register a Patent record originated in."""

    ORANGE_BOOK = "orange_book"
    PURPLE_BOOK = "purple_book"
    USPTO_MANUAL = "uspto_manual"
    LITIGATION = "litigation"
    ARTICLE_CITATION = "article_citation"


class ClaimType(StrEnum):
    """Design doc §5.2 epistemic categories."""

    VERIFIED_FACT = "verified_fact"
    ATTRIBUTED_ANALYSIS = "attributed_analysis"
    PREDICTION = "prediction"
    OPINION = "opinion"
    DISPUTED = "disputed"


class LessonType(StrEnum):
    """Design doc §7.1 Mode 3 categories."""

    STRATEGIC_COMMERCIAL = "strategic_commercial"
    SCIENTIFIC_MECHANISTIC = "scientific_mechanistic"
    REGULATORY_PATHWAY = "regulatory_pathway"
    COMPETITIVE_DYNAMICS = "competitive_dynamics"
    CLINICAL_DEVELOPMENT = "clinical_development"
    MANUFACTURING_CMC = "manufacturing_cmc"
    MARKET_ACCESS_PRICING = "market_access_pricing"


class TrialPhase(StrEnum):
    PRECLINICAL = "preclinical"
    PHASE_1 = "phase_1"
    PHASE_2 = "phase_2"
    PHASE_3 = "phase_3"
    PHASE_4 = "phase_4"
    APPROVED = "approved"
    UNKNOWN = "unknown"


class TrialStatus(StrEnum):
    NOT_YET_RECRUITING = "not_yet_recruiting"
    RECRUITING = "recruiting"
    ACTIVE_NOT_RECRUITING = "active_not_recruiting"
    COMPLETED = "completed"
    TERMINATED = "terminated"
    SUSPENDED = "suspended"
    WITHDRAWN = "withdrawn"
    UNKNOWN = "unknown"


class DrugStatus(StrEnum):
    INVESTIGATIONAL = "investigational"
    APPROVED = "approved"
    WITHDRAWN = "withdrawn"
    DISCONTINUED = "discontinued"


class CredibilityTier(StrEnum):
    """Article credibility tiers (design doc §6.4)."""

    TIER_1_PRIMARY = "tier_1_primary"  # FDA labels, peer-reviewed papers
    TIER_2_VETTED = "tier_2_vetted"  # major outlets (BioPharma Dive, FT, etc.)
    TIER_3_TRADE = "tier_3_trade"  # 公众号, trade press, blogs
    TIER_4_SOCIAL = "tier_4_social"  # Twitter/X, forums
