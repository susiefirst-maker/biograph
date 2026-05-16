"""Curated narrative-fields loader — applies data/curated/<drug>_narrative.yml
to Drug narrative fields (discovery_narrative, mechanism_of_action, their
_zh counterparts, and _source_refs).

Per ADR-0007 merge precedence: curated sources rank higher than ingesters
for narrative fields. The loader stamps field_provenance accordingly.

P2-D4 (retires D-002): wires MergeService.record_conflict so overwrites
of ingester-sourced fields (e.g., Open Targets' short mechanism_of_action)
by curated longer text produce an audit row in merge_conflicts.
"""

from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Drug
from app.services.merge_service import record_conflict


CURATED_DIR = Path(__file__).resolve().parents[3] / "data" / "curated"
NARRATIVE_FILES = sorted(CURATED_DIR.glob("*_narrative.yml"))


# Fields handled by this loader. For each, we set X, X_zh, and
# X_source_refs if the curated entry provides them.
NARRATIVE_FIELDS = ["discovery_narrative", "mechanism_of_action"]

CURATED_SOURCE = "curated:humira_narrative.yml"


def _read_source(provenance: dict[str, Any], field: str) -> str | None:
    """field_provenance may hold either {"source": str} dicts (current
    convention per D-011) or bare strings (legacy rows). Tolerate both."""
    entry = provenance.get(field)
    if isinstance(entry, dict):
        return entry.get("source")
    if isinstance(entry, str):
        return entry
    return None


async def _maybe_log_conflict(
    session: AsyncSession,
    drug: Drug,
    field: str,
    prior_value: Any,
    prior_source: str | None,
    new_value: Any,
) -> None:
    """Log a merge_conflicts row when curated overrides a different ingester value.

    Only fires when there's a genuine prior value that differs AND wasn't
    already curated. Skips the "first-time population" case to keep the
    audit log focused on real overrides.
    """
    if not prior_value:
        return
    if prior_value == new_value:
        return
    if prior_source == CURATED_SOURCE:
        return

    await record_conflict(
        session,
        entity_type="drug",
        entity_id=drug.id,
        field_name=field,
        field_category="narrative",
        source_a=prior_source or "unknown_ingester",
        value_a=prior_value,
        source_b=CURATED_SOURCE,
        value_b=new_value,
        resolution_reason="precedence",
    )


def load_curated_narratives() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in NARRATIVE_FILES:
        if not path.exists():
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        out.extend(doc.get("drugs") or [])
    return out


async def apply_curated_narratives(session: AsyncSession) -> int:
    """Returns count of drug rows updated."""
    entries = load_curated_narratives()
    updated = 0

    for entry in entries:
        chembl_id = entry.get("chembl_id")
        if not chembl_id:
            continue
        drug = await session.scalar(select(Drug).where(Drug.chembl_id == chembl_id))
        if drug is None:
            continue

        drug_changed = False
        provenance = dict(drug.field_provenance or {})

        for field in NARRATIVE_FIELDS:
            # Capture prior state BEFORE mutation so merge-conflict logging
            # sees the ingester-sourced value, not our own write.
            prior_value = getattr(drug, field, None)
            prior_source = _read_source(provenance, field)

            if (text := entry.get(field)) is not None:
                new_value = text.strip() if isinstance(text, str) else text
                await _maybe_log_conflict(
                    session, drug, field, prior_value, prior_source, new_value
                )
                setattr(drug, field, new_value)
                provenance[field] = {"source": CURATED_SOURCE}
                drug_changed = True

            zh_field = f"{field}_zh"
            if (text_zh := entry.get(zh_field)) is not None:
                setattr(drug, zh_field, text_zh.strip() if isinstance(text_zh, str) else text_zh)
                provenance[zh_field] = {"source": CURATED_SOURCE}
                drug_changed = True

            refs_field = f"{field}_source_refs"
            if (refs := entry.get(refs_field)) is not None:
                setattr(drug, refs_field, refs)
                drug_changed = True

        if drug_changed:
            drug.field_provenance = provenance
            updated += 1

    await session.flush()
    return updated
