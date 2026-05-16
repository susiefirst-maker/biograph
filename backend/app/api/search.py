"""Global search — GET /api/search.

Thin wrapper over Meilisearch, plus a preflight landscape-slug match so
that disease/concept queries (NASH, PD-1, CAR-T) surface the curated
landscape page before any same-named company row.
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app.schemas.envelope import ErrorBody, ErrorEnvelope, ListEnvelope, ListMeta
from app.search import search
from app.services.landscape_engine import (
    canonicalize_slug,
    list_curated_slugs,
    load_landscape,
)

router = APIRouter(prefix="/api/search", tags=["search"])

_VALID_TYPES = {"drug", "target", "company", "indication", "landscape"}

_PLURAL = {
    "drug": "drugs",
    "target": "targets",
    "company": "companies",
    "indication": "indications",
}


def _landscape_hits(q: str) -> list[dict[str, Any]]:
    """Return landscape-page hits whose slug, aliases, or display_name match q.

    Ranks curated T1 landscapes ahead of any same-named entity so that queries
    like "NASH" land on the disease landscape rather than a Nashville-based
    company row.
    """
    needle = canonicalize_slug(q)
    if not needle:
        return []
    hits: list[dict[str, Any]] = []
    for slug in list_curated_slugs():
        doc = load_landscape(slug)
        if doc is None:
            continue
        aliases = [a for a in (doc.get("aliases") or []) if isinstance(a, str)]
        candidates = [slug, doc.get("display_name") or "", *aliases]
        canonical_candidates = {canonicalize_slug(c) for c in candidates if c}
        # Exact slug/alias match — highest confidence.
        if needle in canonical_candidates:
            hits.append({
                "entity_type": "landscape",
                "entity_id": slug,
                "display_name": doc.get("display_name") or slug,
                "aliases": aliases[:6],
                "modality": None,
                "link": f"/api/landscape/{slug}",
            })
            continue
        # Substring fallback — "GLP-1" query matches "GLP-1 / Obesity".
        if any(needle and needle in c for c in canonical_candidates):
            hits.append({
                "entity_type": "landscape",
                "entity_id": slug,
                "display_name": doc.get("display_name") or slug,
                "aliases": aliases[:6],
                "modality": None,
                "link": f"/api/landscape/{slug}",
            })
    return hits


@router.get(
    "",
    response_model=ListEnvelope[dict[str, Any]],
    responses={400: {"model": ErrorEnvelope}},
)
async def search_entities(
    q: str = Query(..., min_length=1),
    type: str | None = Query(None),
    limit: int = Query(20, ge=1, le=100),
) -> ListEnvelope[dict[str, Any]]:
    if type is not None and type not in _VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=ErrorBody(
                code="UNKNOWN_ENTITY_TYPE",
                message=f"type must be one of {sorted(_VALID_TYPES)}",
            ).model_dump(),
        )

    results: list[dict[str, Any]] = []

    if type in (None, "landscape"):
        results.extend(_landscape_hits(q))

    if type != "landscape":
        hits = await run_in_threadpool(
            search, q, entity_type=type, limit=limit
        )
        results.extend(
            {
                "entity_type": h["entity_type"],
                "entity_id": h["entity_id"],
                "display_name": h.get("display_name"),
                "aliases": h.get("aliases") or [],
                "modality": h.get("modality"),
                "link": f"/api/{_PLURAL[h['entity_type']]}/{h['entity_id']}",
            }
            for h in hits
        )

    return ListEnvelope[dict[str, Any]](
        data=results[:limit],
        meta=ListMeta(count=len(results[:limit]), entity_type="search_result"),
    )
