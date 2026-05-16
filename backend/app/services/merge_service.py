"""MergeService — ADR-0007 per-field precedence + conflict audit.

Currently declarative (PRECEDENCE by field category) + one utility:
`record_conflict`. Individual ingesters still write their own fields;
the real multi-source merge fires when DrugBank lands (Phase 1+) and
overlaps Open Targets on fields like `modality` / `mechanism_of_action`.

When that happens, ingesters will call `merge_field_value` instead of
writing directly; it looks up precedence, persists the winner, and
records every discrepancy in merge_conflicts.
"""

from typing import Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import MergeConflict


# ADR-0007 — ordered source precedence per field category (highest → lowest).
# Unknown fields fall back to "first writer wins" with a warning logged.
PRECEDENCE: dict[str, list[str]] = {
    "identifier": [],  # no merge — duplicate flag instead
    "naming": ["open_targets", "drugbank", "chembl", "fda", "manual"],
    "molecular": ["drugbank", "chembl", "open_targets"],
    "modality": ["drugbank", "chembl", "open_targets"],
    "regulatory": ["fda", "ema", "pmda", "nmpa", "manual"],
    "phase_status": ["clinicaltrials", "open_targets", "chembl"],
    "target_links": ["open_targets", "drugbank", "chembl"],
    "indication_links": ["open_targets", "chembl", "fda"],
    "trial_links": ["clinicaltrials"],
    "patent_links": ["uspto_manual", "curated", "litigation", "article_citation"],
    "financial": ["sec_edgar", "curated", "manual"],
    "company_metadata": ["sec_edgar", "manual"],
    "narrative": [],  # not merged — hand-authored or LLM (ADR-0006)
}


def resolve_precedence(category: str, source_a: str, source_b: str) -> str:
    """Return whichever source has higher precedence. Tie-break: source_a."""
    order = PRECEDENCE.get(category, [])
    if not order:
        return source_a
    try:
        ia = order.index(source_a)
    except ValueError:
        ia = len(order)
    try:
        ib = order.index(source_b)
    except ValueError:
        ib = len(order)
    return source_a if ia <= ib else source_b


async def record_conflict(
    session: AsyncSession,
    *,
    entity_type: str,
    entity_id: UUID,
    field_name: str,
    field_category: str,
    source_a: str,
    value_a: Any,
    source_b: str,
    value_b: Any,
    resolution_reason: str = "precedence",
    resolved_by: str | None = None,
) -> MergeConflict:
    """Log one audit row. Applies precedence automatically for resolved_*."""
    winner = (
        source_a
        if resolution_reason == "manual_override" and resolved_by
        else resolve_precedence(field_category, source_a, source_b)
    )
    resolved_value = value_a if winner == source_a else value_b

    row = MergeConflict(
        entity_type=entity_type,
        entity_id=entity_id,
        field_name=field_name,
        field_category=field_category,
        source_a=source_a,
        value_a=value_a,
        source_b=source_b,
        value_b=value_b,
        resolved_source=winner,
        resolved_value=resolved_value,
        resolution_reason=resolution_reason,
        resolved_by=resolved_by,
    )
    session.add(row)
    await session.flush()
    return row
