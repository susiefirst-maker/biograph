"""MergeService unit tests — precedence resolution + conflict recording."""

from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

from app.config import settings
from app.models import MergeConflict
from app.services.merge_service import resolve_precedence


def test_precedence_modality_drugbank_wins() -> None:
    """DrugBank > Open Targets for modality per ADR-0007 table."""
    assert resolve_precedence("modality", "drugbank", "open_targets") == "drugbank"
    assert resolve_precedence("modality", "open_targets", "drugbank") == "drugbank"


def test_precedence_regulatory_fda_wins() -> None:
    assert resolve_precedence("regulatory", "fda", "ema") == "fda"


def test_precedence_unknown_category_falls_back_to_first() -> None:
    """Fields we haven't categorized go first-writer-wins."""
    assert resolve_precedence("made_up_category", "alpha", "beta") == "alpha"


def test_precedence_unknown_source_sorts_last() -> None:
    """A source not in the precedence list sorts after known sources."""
    # 'drugbank' is first in molecular; 'beta' unknown → drugbank wins
    assert resolve_precedence("molecular", "drugbank", "beta") == "drugbank"
    assert resolve_precedence("molecular", "beta", "drugbank") == "drugbank"


def test_precedence_narrative_returns_source_a() -> None:
    """narrative is empty list → not merged; returns source_a by fallthrough."""
    assert resolve_precedence("narrative", "humira_manual", "llm_sonnet") == "humira_manual"


@pytest.mark.asyncio
async def test_record_conflict_writes_row() -> None:
    """record_conflict inserts a row and resolves via precedence."""
    from app.services.merge_service import record_conflict

    engine = create_async_engine(settings.database_url)
    async with AsyncSession(engine, expire_on_commit=False) as session:
        entity_id = uuid4()
        row = await record_conflict(
            session,
            entity_type="drug",
            entity_id=entity_id,
            field_name="modality",
            field_category="modality",
            source_a="open_targets",
            value_a="Antibody",
            source_b="drugbank",
            value_b="Biotech",
        )
        await session.commit()

        assert row.resolved_source == "drugbank"  # higher precedence
        assert row.resolved_value == "Biotech"

        # Re-fetch to confirm persistence
        result = await session.scalar(
            select(MergeConflict).where(MergeConflict.id == row.id)
        )
        assert result is not None
        assert result.entity_id == entity_id

        # Cleanup
        await session.delete(result)
        await session.commit()
    await engine.dispose()
