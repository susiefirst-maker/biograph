"""Phase 0-1 acceptance runner for Humira. Thin wrapper over ingest_drug_full.

Hits live APIs: Open Targets + ClinicalTrials.gov + openFDA + SEC EDGAR.
Then applies curated Humira-specific enrichments:
  - drug_financials.yml  ($20.7B peak)
  - drug_patents.yml     (US6090382 anchor)
  - deals.yml            (Abbott-Knoll, AbbVie-Allergan)
  - humira_events.yml    (15 events, causal chains)
  - humira_narrative.yml (bilingual golden narrative)
  - humira_articles.yml  (6 articles, CN + EN)
  - humira_claims.yml    (7 claims, 4 claim types)
  - humira_lessons.yml   (3 lessons per §14.2)
  - humira_biosimilars.yml (10 Humira biosimilars)

Run:
  cd backend && source .venv/bin/activate
  PYTHONPATH=. python scripts/ingest_adalimumab.py

Exit 0 = acceptance green; non-zero = failure.

For fixture-only offline seeding (no live API calls), use scripts/seed_phase_0.py.
"""

import asyncio
import sys

from app.db import get_session
from app.services.curated_articles import apply_curated_articles
from app.services.curated_biosimilars import apply_curated_biosimilars
from app.services.curated_claims import apply_curated_claims
from app.services.curated_deals import apply_curated_deals
from app.services.curated_events import apply_curated_events
from app.services.curated_financials import apply_curated_financials
from app.services.curated_lessons import apply_curated_lessons
from app.services.curated_narrative import apply_curated_narratives
from app.services.curated_patents import apply_curated_patents
from app.services.drug_ingest import (
    DrugIngestSpec,
    fetch_drug_summary,
    ingest_drug_full,
)


HUMIRA_SPEC = DrugIngestSpec(
    chembl_id="CHEMBL1201580",
    generic_name="adalimumab",
    originator_tickers=["ABBV", "ABT"],
)


async def _apply_all_curated() -> dict[str, int]:
    """Apply every curated YAML. Returns per-loader counts."""
    counts: dict[str, int] = {}
    loaders = [
        ("financials", apply_curated_financials),
        ("patents", apply_curated_patents),
        ("deals", apply_curated_deals),
        ("events", apply_curated_events),
        ("narratives", apply_curated_narratives),
        ("articles", apply_curated_articles),
        ("claims", apply_curated_claims),
        ("lessons", apply_curated_lessons),
        ("biosimilars", apply_curated_biosimilars),
    ]
    for name, fn in loaders:
        async with get_session() as session:
            counts[name] = await fn(session)
    return counts


async def main() -> int:
    # Step 1-4: orchestrator runs Open Targets + CT.gov + FDA + SEC
    report = await ingest_drug_full(HUMIRA_SPEC)
    print(f"=== {HUMIRA_SPEC.generic_name} live ingest report ===")
    print(f"drug_id: {report.drug_id}")
    print(f"targets: {report.target_count}")
    print(f"indications: {report.indication_count}")
    print(f"trials: {report.trials_count} of {report.ct_total_available} available")
    print(f"regulatory_decisions: {report.regulatory_decisions_total} total, "
          f"{report.regulatory_decisions_linked} linked to originator")
    print(f"SEC companies: {[c.get('ticker') for c in report.companies_resolved_from_sec]}")

    # Step 5: curated enrichments
    counts = await _apply_all_curated()
    for name, n in counts.items():
        print(f"  curated/{name}: {n}")

    # Read-back + Humira-specific acceptance assertions
    summary = await fetch_drug_summary(HUMIRA_SPEC.chembl_id)
    assert summary, "Humira not persisted"
    assert any("TNF" in (t[0] or "") for t in summary["targets"])
    assert len(summary["trials"]) >= 30
    assert len(summary["regulatory_decisions"]) >= 5
    assert summary["revenue_peak_usd"] and summary["revenue_peak_usd"] >= 20_000_000_000
    assert any(p[0] == "6090382" for p in summary["patents"])

    print(f"\nHumira live-ingest acceptance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
