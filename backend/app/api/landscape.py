"""Landscape route — GET /api/landscape/{slug}.

T1 (curator-compiled) only for P5-D4. Envelope shape per ADR-0011.
Language fallback: ?lang=zh returns zh variants where present; EN is
the default.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.schemas.envelope import ErrorBody, ErrorEnvelope
from app.schemas.landscape import LandscapeEnvelope, LandscapeMeta
from app.services.landscape_engine import (
    canonicalize_slug,
    derive_related,
    list_curated_slugs,
    load_landscape,
)

router = APIRouter(prefix="/api/landscape", tags=["landscape"])


@router.get("")
async def list_landscapes() -> dict[str, Any]:
    """Shallow index of all T1-curated landscapes — slug + display name."""
    entries: list[dict[str, Any]] = []
    for slug in list_curated_slugs():
        doc = load_landscape(slug)
        if doc is None:
            continue
        entries.append(
            {
                "slug": doc.get("slug", slug),
                "display_name": doc.get("display_name", slug),
                "quality_tier": doc.get("quality_tier", "T3_EXPLORATORY"),
                "last_curated_at": str(doc.get("last_curated_at") or ""),
            }
        )
    return {"data": entries, "meta": {"count": len(entries)}}


TIER_LABELS = {
    "T1_CURATED": ("Expert-compiled landscape", "专家编译"),
    "T2_STRUCTURED": ("Data-compiled landscape", "数据编译"),
    "T3_EXPLORATORY": ("Auto-compiled (beta)", "自动编译 (beta)"),
}


@router.get(
    "/{slug}",
    response_model=LandscapeEnvelope,
    responses={404: {"model": ErrorEnvelope}},
)
async def get_landscape(
    slug: str,
    lang: str = Query("en", pattern="^(en|zh)$"),
) -> LandscapeEnvelope:
    doc = load_landscape(slug)
    if doc is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="LANDSCAPE_NOT_FOUND",
                message=f"No landscape curated for slug={canonicalize_slug(slug)}",
            ).model_dump(),
        )

    data = _apply_lang(doc, lang)
    lang_fallback = lang == "zh" and not _has_zh_content(doc)

    tier = doc.get("quality_tier", "T3_EXPLORATORY")
    en_label, zh_label = TIER_LABELS.get(tier, TIER_LABELS["T3_EXPLORATORY"])

    related_landscapes = [
        {
            "slug": r["slug"],
            "display_name": r["display_name"],
            "shared_drugs": r["shared_drugs"],
            "shared_targets": r["shared_targets"],
            "link": f"/api/landscape/{r['slug']}",
        }
        for r in derive_related(doc.get("slug", canonicalize_slug(slug)))
    ]

    return LandscapeEnvelope(
        data=data,
        meta=LandscapeMeta(
            slug=doc.get("slug", canonicalize_slug(slug)),
            quality_tier=tier,
            tier_label_en=en_label,
            tier_label_zh=zh_label,
            data_completeness_score=_score(doc),
            human_reviewed=bool(doc.get("human_reviewed")),
            last_curated_at=doc.get("last_curated_at"),
            sources=_sources(doc),
            lang_fallback=lang_fallback,
        ),
        related={"landscapes": related_landscapes} if related_landscapes else {},
    )


def _apply_lang(doc: dict[str, Any], lang: str) -> dict[str, Any]:
    """Surface `_zh` variants when lang=zh, strip meta-only fields from `data`.

    Meta-ish fields (quality_tier, human_reviewed, aliases) live on
    `meta`; the envelope's `data` block carries the user-facing payload.
    """
    meta_keys = {
        "quality_tier",
        "last_curated_at",
        "human_reviewed",
        "aliases",
    }
    result: dict[str, Any] = {}
    for key, value in doc.items():
        if key in meta_keys:
            continue
        if lang == "zh":
            zh_key = f"{key}_zh"
            if zh_key in doc and doc[zh_key]:
                result[key] = doc[zh_key]
                continue
            if key.endswith("_zh"):
                continue  # don't duplicate zh variants at top level
        else:
            if key.endswith("_zh"):
                continue
        result[key] = value
    return result


def _has_zh_content(doc: dict[str, Any]) -> bool:
    return any(k.endswith("_zh") and v for k, v in doc.items())


def _score(doc: dict[str, Any]) -> float:
    """Rough completeness score over the 10 major landscape sections."""
    checks = [
        bool(doc.get("disease_overview")) and len(doc["disease_overview"]) > 200,
        bool(doc.get("mechanism_map")),
        bool(doc.get("pipeline")),
        bool(doc.get("companies")) and len(doc["companies"]) >= 3,
        bool(doc.get("key_trials")),
        bool(doc.get("scientific_bottlenecks")) and len(doc["scientific_bottlenecks"]) >= 3,
        bool(doc.get("market_dynamics")),
        bool(doc.get("regulatory_context")),
        bool(doc.get("hot_targets")) and len(doc["hot_targets"]) >= 4,
        bool(doc.get("literature")) and len(doc["literature"]) >= 3,
    ]
    return round(sum(checks) / len(checks), 2)


def _sources(doc: dict[str, Any]) -> list[str]:
    """Distinct source_name values mentioned across the literature + articles sections."""
    sources: set[str] = set()
    for lit in doc.get("literature", []) or []:
        if isinstance(lit, dict) and (j := lit.get("journal")):
            sources.add(str(j))
    for art in doc.get("articles", []) or []:
        if isinstance(art, dict) and (s := art.get("source_name")):
            sources.add(str(s))
    return sorted(sources)
