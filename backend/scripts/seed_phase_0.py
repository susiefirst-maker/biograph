"""Seed Phase 0 + Phase 1 Day 1 state from committed fixtures — no network.

CI and offline-dev entry point. Produces the same DB state as
`ingest_adalimumab.py` by replaying both the Open Targets fixture
(1 drug, 1 target, 34 indications) and the CT.gov fixture (40 trials,
≥1 sponsor Company).

Run:
  PYTHONPATH=. python scripts/seed_phase_0.py

Use `ingest_adalimumab.py` to refresh fixtures from live APIs.
"""

import asyncio
import json
import sys
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.ingestion.clinicaltrials import ClinicalTrialsIngester
from app.ingestion.open_targets import OpenTargetsIngester
from app.models import Drug
from app.services.clinical_trial_service import upsert_clinical_trials_from_ctgov
from app.services.drug_service import upsert_drug_from_open_targets


FIXTURES = Path(__file__).resolve().parent.parent / "tests" / "fixtures"
OT_FIXTURE = FIXTURES / "open_targets_CHEMBL1201580.json"
CT_FIXTURE = FIXTURES / "clinicaltrials_adalimumab.json"
FDA_FIXTURE = FIXTURES / "fda_adalimumab.json"
SEC_ABBV_FIXTURE = FIXTURES / "sec_abbv_raw.json"
CHEMBL_ID = "CHEMBL1201580"


async def main() -> int:
    for f in (OT_FIXTURE, CT_FIXTURE, FDA_FIXTURE, SEC_ABBV_FIXTURE):
        if not f.exists():
            print(f"FAIL: fixture not found at {f}", file=sys.stderr)
            return 1

    # Open Targets — drug + targets + indications
    ot_raw = json.loads(OT_FIXTURE.read_text())
    ot_normalized = OpenTargetsIngester().normalize(ot_raw)
    async with get_session() as session:
        drug = await upsert_drug_from_open_targets(session, ot_normalized)
        drug_id = drug.id

    # ClinicalTrials.gov — trials + sponsor companies, linked to drug
    ct_raw = json.loads(CT_FIXTURE.read_text())
    ct_normalized = ClinicalTrialsIngester().normalize(ct_raw)
    async with get_session() as session:
        trials = await upsert_clinical_trials_from_ctgov(session, drug_id, ct_normalized)

    # openFDA — regulatory decisions (originator + biosimilars; only originator linked to drug)
    from app.ingestion.fda import FDAIngester
    from app.ingestion.sec_edgar import SECEdgarIngester
    from app.services.curated_financials import apply_curated_financials
    from app.services.regulatory_decision_service import (
        upsert_regulatory_decisions_from_fda,
    )
    from app.services.sec_service import upsert_company_from_sec

    fda_raw = json.loads(FDA_FIXTURE.read_text())
    fda_raw["_query_generic"] = "adalimumab"
    fda_normalized = FDAIngester().normalize(fda_raw)
    async with get_session() as session:
        decisions = await upsert_regulatory_decisions_from_fda(session, drug_id, fda_normalized)

    # SEC EDGAR — AbbVie Company entity (CIK + ticker + name)
    sec_raw = json.loads(SEC_ABBV_FIXTURE.read_text())
    sec_normalized = SECEdgarIngester().normalize(sec_raw)
    async with get_session() as session:
        await upsert_company_from_sec(session, sec_normalized)

    # Curated — product-level financials (Humira $20.7B peak)
    async with get_session() as session:
        curated_count = await apply_curated_financials(session)

    # Curated — patents (Phase 1 Day 4; anchor only until PatentsView key lands)
    from app.services.curated_patents import apply_curated_patents

    async with get_session() as session:
        patent_count = await apply_curated_patents(session)

    # Curated — deals (Phase 1 Day 8 / ADR-0012; Abbott-Knoll + AbbVie-Allergan)
    from app.services.curated_deals import apply_curated_deals

    async with get_session() as session:
        deal_count = await apply_curated_deals(session)

    # Curated — events (Phase 1 Day 8-C; 15+ Humira timeline events + causal chains)
    from app.services.curated_events import apply_curated_events

    async with get_session() as session:
        event_count = await apply_curated_events(session)

    # Curated — narratives (Phase 1 Day 8-A; hand-authored Humira golden narrative)
    from app.services.curated_narrative import apply_curated_narratives

    async with get_session() as session:
        narrative_count = await apply_curated_narratives(session)

    # Curated — articles (P2-D1; Humira source articles CN + EN)
    from app.services.curated_articles import apply_curated_articles

    async with get_session() as session:
        article_count = await apply_curated_articles(session)

    # Curated — claims (P2-D2; hand-curated Humira claims linked to articles)
    from app.services.curated_claims import apply_curated_claims

    async with get_session() as session:
        claim_count = await apply_curated_claims(session)

    # Curated — lessons (P2-D3; 3 Humira lessons per §14.2)
    from app.services.curated_lessons import apply_curated_lessons

    async with get_session() as session:
        lesson_count = await apply_curated_lessons(session)

    # Curated — biosimilars (P2-D3; 10 Humira biosimilars linked via biosimilar_of_id)
    from app.services.curated_biosimilars import apply_curated_biosimilars

    async with get_session() as session:
        biosimilar_count = await apply_curated_biosimilars(session)

    async with get_session() as session:
        result = await session.scalar(
            select(Drug)
            .where(Drug.id == drug_id)
            .options(
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
        assert result is not None
        assert len(list(result.trials)) >= 30
        assert len(list(result.regulatory_decisions)) >= 5
        assert result.revenue_peak_usd is not None and result.revenue_peak_usd >= 20_000_000_000
        assert any(p.patent_number == "6090382" for p in result.patents)
        assert any("Abbott" in (d.headline or "") for d in result.deals)
        assert len(list(result.events)) >= 15

    linked_decisions = sum(1 for d in decisions if d.drug_id == drug_id)
    print(
        f"seeded from fixtures: 1 drug (adalimumab), "
        f"{len(ot_normalized['targets'])} target, "
        f"{len(ot_normalized['indications'])} indications, "
        f"{len(trials)} trials, "
        f"{len(decisions)} regulatory decisions ({linked_decisions} linked to Humira), "
        f"1 SEC-resolved Company (AbbVie), "
        f"curated financials on {curated_count} drug(s) "
        f"(Humira peak ${result.revenue_peak_usd / 1e9:.1f}B), "
        f"{patent_count} curated patent row(s), "
        f"{deal_count} curated deal pairing(s), "
        f"{event_count} curated events, "
        f"narratives on {narrative_count} drug(s), "
        f"{article_count} curated articles, "
        f"{claim_count} curated claims, "
        f"{lesson_count} curated lessons, "
        f"{biosimilar_count} curated biosimilars"
    )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
