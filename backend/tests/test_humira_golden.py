"""Humira regression test — entity-axis quality gate.

Per design doc §11.3 + ADR-0008. 14 requirements from Humira's golden-
entity spec. Each runs against the persisted adalimumab Drug record.

Current state (Phase 0 Day 5):
  - 2 requirements pass (tnf_target, has_indications) — ingested Day 4
  - 12 requirements xfail with strict=True, each tagged to the Phase that
    will make it pass. A silent XPASS fails CI → forces reviewer to
    remove the marker when its Phase lands.

Run:
  pytest tests/test_humira_golden.py -v

Prerequisite:
  scripts/ingest_adalimumab.py has run at least once against the current DB.
"""

from typing import Callable

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.models import Drug


CHEMBL_ID = "CHEMBL1201580"


# Read-only regression checks use a sync engine — avoids pytest-asyncio's
# per-test-loop disposal conflicting with asyncpg's connection pool.
# Write paths (ingesters, services) stay async per ADR-0003.
_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


@pytest.fixture
def humira() -> Drug:
    """Load adalimumab with eagerly-loaded Day-0 relationships."""
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
                selectinload(Drug.biosimilars),
            )
        )
        if drug is None:
            pytest.skip(
                "adalimumab not in DB — run `python scripts/ingest_adalimumab.py` first."
            )
        return drug


# ── Requirements ────────────────────────────────────────────────────────────
# Shape: (id, check, xfail_reason | None)
#   xfail_reason=None → must pass today
#   xfail_reason="..." → marked xfail(strict=True); the Phase that will
#                        make it pass is named in the reason.

HUMIRA_REQUIREMENTS: list[tuple[str, Callable[[Drug], bool], str | None]] = [
    # GREEN from Day 4 (Open Targets ingest)
    (
        "tnf_target",
        lambda d: any("TNF" in (t.gene_symbol or "") for t in d.targets),
        None,
    ),
    (
        "has_indications",
        lambda d: len(d.indications) >= 10,
        None,
    ),
    # GREEN from Phase 1 Day 1 (ClinicalTrials.gov ingest)
    (
        "trials_count",
        lambda d: len(d.trials) >= 30,
        None,
    ),
    # GREEN from Phase 1 Day 2 (openFDA Drugs@FDA ingest)
    (
        "regulatory_decisions_count",
        lambda d: len(d.regulatory_decisions) >= 5,
        None,
    ),
    # GREEN from Phase 1 Day 3 (curated drug financials — Humira $20.7B peak, 2021)
    (
        "revenue_peak",
        lambda d: (d.revenue_peak_usd or 0) >= 20_000_000_000,
        None,
    ),
    # GREEN from Phase 1 Day 4 (curated anchor patent US6090382)
    (
        "has_core_patent",
        lambda d: any(p.patent_number == "6090382" for p in d.patents),
        None,
    ),
    # GREEN from Phase 1 Day 8 / ADR-0012 (Deal promotion + curated Humira deals)
    (
        "abbott_acquisition",
        lambda d: any("Abbott" in (deal.headline or "") for deal in d.deals),
        None,
    ),
    # GREEN from Phase 1 Day 8-C (curated Humira event timeline)
    (
        "abbvie_spinoff",
        lambda d: any("spinoff" in (e.event_type or "") for e in d.events),
        None,
    ),
    (
        "has_timeline",
        lambda d: len(d.events) >= 15,
        None,
    ),
    (
        "causal_chain_exists",
        lambda d: any(e.triggered_by is not None for e in d.events),
        None,
    ),
    # GREEN from Phase 1 Day 8-A (curated Humira narrative — hand-authored, §14.1)
    (
        "discovery_origin",
        lambda d: bool(d.discovery_narrative) and ("BASF" in d.discovery_narrative or "Knoll" in d.discovery_narrative),
        None,
    ),
    (
        "phage_display",
        lambda d: "phage" in (d.discovery_narrative or "").lower(),
        None,
    ),
    (
        "has_chinese_narrative",
        lambda d: d.discovery_narrative_zh is not None and len(d.discovery_narrative_zh) > 50,
        None,
    ),
    # GREEN from P2-D2 (curated Humira claims — 7 across 4 claim types)
    (
        "has_claims",
        lambda d: len(d.claims) >= 5,
        None,
    ),
    # GREEN from P2-D3 (3 hand-authored Humira lessons per §14.2)
    (
        "has_lessons",
        lambda d: len(d.lessons) >= 2,
        None,
    ),
    # GREEN from P2-D3 (biosimilar_of_id schema + 10 curated Humira biosimilars)
    (
        "biosimilars_exist",
        lambda d: len(d.biosimilars) >= 6,
        None,
    ),

    # XFAIL — remaining external blocker
    (
        "patent_thicket",
        lambda d: len(getattr(d, "patents", []) or []) > 100,
        "Phase 1 Day 5+: Blocked on PatentsView API key registration "
        "(https://patentsview.org/api-key-request) OR authoritative Humira "
        "patent-list paste (I-MAK appendix / Harvard Petrie-Flom) into "
        "data/curated/drug_patents.yml. Anchor patent US6090382 seeded Day 4; "
        "count (1) well below threshold (100).",
    ),
]


def _make_params() -> list:
    """Build parametrize list; attach xfail marker per-case when a Phase-target reason is set."""
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
        for name, check, reason in HUMIRA_REQUIREMENTS
    ]


@pytest.mark.parametrize("name, check", _make_params())
def test_humira_requirement(humira: Drug, name: str, check: Callable[[Drug], bool]) -> None:
    """One Humira regression assertion. See HUMIRA_REQUIREMENTS."""
    assert check(humira), f"Humira requirement '{name}' failed"
