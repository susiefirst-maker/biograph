"""Graph neighbor traversal — reads from the entity_relationships VIEW.

Depth=1 is a single SELECT; depth=2 uses a recursive CTE (design doc §8.3).
Nodes include the root as distance=0. Labels are hydrated per-type via
one batched SELECT per type present in the neighborhood.
"""

from typing import Iterable
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api._deps import db
from app.models import (
    Claim,
    ClinicalTrial,
    Company,
    Deal,
    Drug,
    Event,
    Indication,
    Lesson,
    Patent,
    RegulatoryDecision,
    Target,
)
from app.schemas.envelope import ErrorBody, ErrorEnvelope
from app.schemas.graph import GraphData, GraphEdge, GraphEnvelope, GraphMeta, GraphNode

router = APIRouter(prefix="/api/graph", tags=["graph"])

# entity_type → (Model, label column name). Must match the strings emitted
# by the entity_relationships VIEW (see Phase 1 Day 8 migration).
_LABELS: dict[str, tuple[type, str]] = {
    "drug": (Drug, "generic_name"),
    "target": (Target, "gene_symbol"),
    "company": (Company, "name"),
    "indication": (Indication, "name"),
    "clinical_trial": (ClinicalTrial, "nct_id"),
    "regulatory_decision": (RegulatoryDecision, "application_number"),
    "patent": (Patent, "patent_number"),
    "event": (Event, "headline"),
    "claim": (Claim, "statement"),
    "lesson": (Lesson, "title"),
    "deal": (Deal, "headline"),
}

_VALID_TYPES = set(_LABELS.keys())

_DEPTH_1_SQL = text(
    """
    SELECT target_type, target_id, relationship_type
    FROM entity_relationships
    WHERE source_type = :root_type AND source_id = :root_id
    """
)

_DEPTH_2_SQL = text(
    """
    WITH RECURSIVE graph AS (
        SELECT source_type, source_id, target_type, target_id,
               relationship_type, 1 AS distance
        FROM entity_relationships
        WHERE source_type = :root_type AND source_id = :root_id

        UNION ALL

        SELECT er.source_type, er.source_id, er.target_type, er.target_id,
               er.relationship_type, g.distance + 1
        FROM entity_relationships er
        JOIN graph g
          ON er.source_type = g.target_type
         AND er.source_id   = g.target_id
        WHERE g.distance < :max_depth
          AND NOT (er.target_type = :root_type AND er.target_id = :root_id)
    )
    SELECT source_type, source_id, target_type, target_id,
           relationship_type, MIN(distance) AS distance
    FROM graph
    GROUP BY source_type, source_id, target_type, target_id, relationship_type
    """
)


@router.get(
    "/neighbors/{entity_type}/{entity_id}",
    response_model=GraphEnvelope,
    responses={400: {"model": ErrorEnvelope}, 404: {"model": ErrorEnvelope}},
)
async def get_neighbors(
    entity_type: str,
    entity_id: UUID,
    depth: int = Query(1, ge=1, le=2),
    session: AsyncSession = Depends(db),
) -> GraphEnvelope:
    if entity_type not in _VALID_TYPES:
        raise HTTPException(
            status_code=400,
            detail=ErrorBody(
                code="UNKNOWN_ENTITY_TYPE",
                message=f"entity_type must be one of {sorted(_VALID_TYPES)}",
            ).model_dump(),
        )

    root_label = await _fetch_label(session, entity_type, entity_id)
    if root_label is None:
        raise HTTPException(
            status_code=404,
            detail=ErrorBody(
                code="ENTITY_NOT_FOUND",
                message=f"{entity_type} with id={entity_id} not found",
            ).model_dump(),
        )

    if depth == 1:
        rows = await session.execute(
            _DEPTH_1_SQL, {"root_type": entity_type, "root_id": entity_id}
        )
        raw_edges = [(entity_type, entity_id, r[0], r[1], r[2], 1) for r in rows]
    else:
        rows = await session.execute(
            _DEPTH_2_SQL,
            {"root_type": entity_type, "root_id": entity_id, "max_depth": depth},
        )
        raw_edges = [(r[0], r[1], r[2], r[3], r[4], r[5]) for r in rows]

    # Collect distinct (type, id) pairs + per-node minimum distance.
    distances: dict[tuple[str, UUID], int] = {(entity_type, entity_id): 0}
    for src_t, src_id, tgt_t, tgt_id, _rel, dist in raw_edges:
        node_key = (tgt_t, tgt_id)
        if node_key not in distances or distances[node_key] > dist:
            distances[node_key] = dist

    labels = await _hydrate_labels(session, distances.keys())

    source_node = GraphNode(
        type=entity_type,
        id=entity_id,
        label=root_label,
        link=f"/api/{_plural(entity_type)}/{entity_id}",
        distance=0,
    )
    nodes = [source_node] + [
        GraphNode(
            type=t,
            id=i,
            label=labels.get((t, i)),
            link=f"/api/{_plural(t)}/{i}",
            distance=d,
        )
        for (t, i), d in distances.items()
        if (t, i) != (entity_type, entity_id)
    ]
    edges = [
        GraphEdge(
            source_type=s_t,
            source_id=s_i,
            target_type=t_t,
            target_id=t_i,
            relationship_type=rel,
        )
        for s_t, s_i, t_t, t_i, rel, _d in raw_edges
    ]

    return GraphEnvelope(
        data=GraphData(source=source_node, nodes=nodes, edges=edges),
        meta=GraphMeta(
            entity_type="graph",
            root_type=entity_type,
            depth=depth,
            node_count=len(nodes),
            edge_count=len(edges),
        ),
    )


async def _fetch_label(session: AsyncSession, entity_type: str, entity_id: UUID) -> str | None:
    model, col = _LABELS[entity_type]
    stmt = select(getattr(model, col)).where(model.id == entity_id)
    return await session.scalar(stmt)


async def _hydrate_labels(
    session: AsyncSession, keys: Iterable[tuple[str, UUID]]
) -> dict[tuple[str, UUID], str | None]:
    by_type: dict[str, list[UUID]] = {}
    for t, i in keys:
        by_type.setdefault(t, []).append(i)

    labels: dict[tuple[str, UUID], str | None] = {}
    for t, ids in by_type.items():
        model, col = _LABELS[t]
        stmt = select(model.id, getattr(model, col)).where(model.id.in_(ids))
        for row_id, row_label in (await session.execute(stmt)).all():
            labels[(t, row_id)] = row_label
    return labels


def _plural(entity_type: str) -> str:
    """Map entity_type to API route plural (used for `link` fields)."""
    irregular = {
        "company": "companies",
        "indication": "indications",
        "clinical_trial": "clinical-trials",
        "regulatory_decision": "regulatory-decisions",
    }
    return irregular.get(entity_type, f"{entity_type}s")
