"""P5-D1 — Ozempic (semaglutide, Novo Nordisk) acceptance runner.

Third golden entity. Same orchestrator + glob-based curated loaders as
ingest_adalimumab.py and ingest_keytruda.py. Validates the framework
extends beyond antibodies to a long-acting peptide with a metabolic /
obesity commercial narrative.

Run:
  cd backend && source .venv/bin/activate
  PYTHONPATH=. python scripts/ingest_ozempic.py
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


OZEMPIC_SPEC = DrugIngestSpec(
    chembl_id="CHEMBL2108724",
    generic_name="semaglutide",
    originator_tickers=["NVO"],  # Novo Nordisk ADR
)


async def _apply_all_curated() -> dict[str, int]:
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
    report = await ingest_drug_full(OZEMPIC_SPEC)
    print(f"=== {OZEMPIC_SPEC.generic_name} live ingest report ===")
    print(f"drug_id: {report.drug_id}")
    print(f"targets: {report.target_count}")
    print(f"indications: {report.indication_count}")
    print(f"trials: {report.trials_count} of {report.ct_total_available} available")
    print(f"regulatory_decisions: {report.regulatory_decisions_total} total, "
          f"{report.regulatory_decisions_linked} linked")
    print(f"SEC companies: {[c.get('ticker') for c in report.companies_resolved_from_sec]}")

    counts = await _apply_all_curated()
    for name, n in counts.items():
        print(f"  curated/{name}: {n}")

    summary = await fetch_drug_summary(OZEMPIC_SPEC.chembl_id)
    assert summary
    assert any("GLP1R" in (t[0] or "") for t in summary["targets"])
    assert len(summary["trials"]) >= 10
    assert summary["revenue_peak_usd"] and summary["revenue_peak_usd"] >= 20_000_000_000
    assert any(p[0] == "8129343" for p in summary["patents"])

    print(f"\nOzempic acceptance: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
