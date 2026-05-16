"""LandscapeEnvelope per ADR-0011.

Distinct from EntityEnvelope — tier metadata in `meta.quality_tier`,
`related.landscapes` for sibling landscape chips (empty for P5-D4 T1
implementation, populated when ≥2 T1 landscapes overlap).
"""

from __future__ import annotations

from datetime import date
from typing import Any

from pydantic import BaseModel


class LandscapeMeta(BaseModel):
    entity_type: str = "landscape"
    slug: str
    quality_tier: str  # T1_CURATED / T2_STRUCTURED / T3_EXPLORATORY
    tier_label_en: str
    tier_label_zh: str
    data_completeness_score: float
    human_reviewed: bool
    last_curated_at: date | None = None
    sources: list[str] = []
    lang_fallback: bool = False


class LandscapeEnvelope(BaseModel):
    data: dict[str, Any]
    meta: LandscapeMeta
    related: dict[str, list[dict[str, Any]]] = {}
