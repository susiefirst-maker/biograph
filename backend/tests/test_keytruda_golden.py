"""Keytruda regression test — second golden entity.

Exercises the same framework as test_humira_golden but on a different
drug (pembrolizumab, CHEMBL3137343). Purpose: prove that the curated-
loader + golden-entity pattern works on Keytruda's PD-1 narrative
without framework code changes.

Current state (P2-D5): 10 assertions. All hit the curated data added
via keytruda_*.yml files only; no new Python code path.
"""

from typing import Callable

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import Drug


CHEMBL_ID = "CHEMBL3137343"  # pembrolizumab
_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


@pytest.fixture
def keytruda() -> Drug:
    with Session(_sync_engine, expire_on_commit=False) as session:
        drug = session.scalar(
            select(Drug)
            .where(Drug.chembl_id == CHEMBL_ID)
            .options(
                selectinload(Drug.targets),
                selectinload(Drug.indications),
                selectinload(Drug.trials),
                selectinload(Drug.regulatory_decisions),
                selectinload(Drug.patents),
                selectinload(Drug.deals),
                selectinload(Drug.events),
                selectinload(Drug.claims),
                selectinload(Drug.lessons),
            )
        )
        if drug is None:
            pytest.skip(
                "Keytruda (CHEMBL3137343) not ingested — run "
                "`PYTHONPATH=. python scripts/ingest_keytruda.py` first."
            )
        return drug


KEYTRUDA_REQUIREMENTS: list[tuple[str, Callable[[Drug], bool], str | None]] = [
    ("pd1_target", lambda d: any("PDCD1" in (t.gene_symbol or "") for t in d.targets), None),
    ("has_indications", lambda d: len(d.indications) >= 10, None),
    ("trials_count", lambda d: len(d.trials) >= 100, None),
    ("regulatory_decisions_count", lambda d: len(d.regulatory_decisions) >= 5, None),
    # Curated data — from keytruda_*.yml files added in P2-D5
    (
        "revenue_peak_2023",
        lambda d: (d.revenue_peak_usd or 0) >= 20_000_000_000 and d.revenue_peak_year == 2023,
        None,
    ),
    (
        "has_core_patent",
        lambda d: any(p.patent_number == "8354509" for p in d.patents),
        None,
    ),
    (
        "organon_origin",
        lambda d: bool(d.discovery_narrative) and "Organon" in d.discovery_narrative,
        None,
    ),
    (
        "pd1_mechanism",
        lambda d: bool(d.discovery_narrative) and "PD-1" in d.discovery_narrative,
        None,
    ),
    (
        "has_chinese_narrative",
        lambda d: d.discovery_narrative_zh is not None and len(d.discovery_narrative_zh) > 50,
        None,
    ),
    (
        "has_timeline",
        lambda d: len(d.events) >= 10,
        None,
    ),
    (
        "causal_chain_exists",
        lambda d: any(e.triggered_by is not None for e in d.events),
        None,
    ),
    (
        "merck_sp_deal",
        lambda d: any("Schering-Plough" in (deal.headline or "") for deal in d.deals),
        None,
    ),
    (
        "has_claims",
        lambda d: len(d.claims) >= 3,
        None,
    ),
    (
        "has_lessons",
        lambda d: len(d.lessons) >= 2,
        None,
    ),
]


def _make_params() -> list:
    return [
        pytest.param(
            name,
            check,
            id=name,
            marks=(
                [pytest.mark.xfail(reason=reason, strict=True, raises=(AssertionError, AttributeError, TypeError))]
                if reason
                else []
            ),
        )
        for name, check, reason in KEYTRUDA_REQUIREMENTS
    ]


@pytest.mark.parametrize("name, check", _make_params())
def test_keytruda_requirement(keytruda: Drug, name: str, check: Callable[[Drug], bool]) -> None:
    """One Keytruda regression assertion. See KEYTRUDA_REQUIREMENTS."""
    assert check(keytruda), f"Keytruda requirement '{name}' failed"
