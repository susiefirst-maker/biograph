"""Ozempic (semaglutide) regression test — third golden entity.

Exercises the same framework as test_humira_golden / test_keytruda_golden.
Purpose: prove the curated-loader + golden-entity pattern works on a
long-acting peptide with a metabolic/obesity commercial narrative, not
just antibodies.

Current state (P5-D1): 13 assertions. All hit the curated data added
via ozempic_*.yml files only; no new Python code path.
"""

from typing import Callable

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import Drug


CHEMBL_ID = "CHEMBL2108724"  # semaglutide
_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


@pytest.fixture
def ozempic() -> Drug:
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
                "Ozempic (CHEMBL2108724) not ingested — run "
                "`PYTHONPATH=. python scripts/ingest_ozempic.py` first."
            )
        return drug


OZEMPIC_REQUIREMENTS: list[tuple[str, Callable[[Drug], bool], str | None]] = [
    ("glp1r_target", lambda d: any("GLP1R" in (t.gene_symbol or "") for t in d.targets), None),
    ("has_indications", lambda d: len(d.indications) >= 2, None),
    ("trials_count", lambda d: len(d.trials) >= 10, None),
    # Curated data — from ozempic_*.yml files added in P5-D1
    (
        "revenue_peak_2023",
        lambda d: (d.revenue_peak_usd or 0) >= 20_000_000_000 and d.revenue_peak_year == 2023,
        None,
    ),
    (
        "has_composition_patent",
        lambda d: any(p.patent_number == "8129343" for p in d.patents),
        None,
    ),
    (
        "has_oral_formulation_patent",
        lambda d: any(p.patent_number == "8536122" for p in d.patents),
        None,
    ),
    (
        "novo_origin",
        lambda d: bool(d.discovery_narrative) and "Novo Nordisk" in d.discovery_narrative,
        None,
    ),
    (
        "glp1_mechanism",
        lambda d: bool(d.discovery_narrative) and "GLP-1" in d.discovery_narrative,
        None,
    ),
    (
        "peptide_engineering_detail",
        lambda d: bool(d.mechanism_of_action) and "half-life" in d.mechanism_of_action.lower(),
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
        "emisphere_deal",
        lambda d: any("Emisphere" in (deal.headline or "") for deal in d.deals),
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
        for name, check, reason in OZEMPIC_REQUIREMENTS
    ]


@pytest.mark.parametrize("name, check", _make_params())
def test_ozempic_requirement(ozempic: Drug, name: str, check: Callable[[Drug], bool]) -> None:
    """One Ozempic regression assertion. See OZEMPIC_REQUIREMENTS."""
    assert check(ozempic), f"Ozempic requirement '{name}' failed"
