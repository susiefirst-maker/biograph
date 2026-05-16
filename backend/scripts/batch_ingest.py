"""Batch ingest — runs `ingest_drug_full` over the curated 100-drug list.

Each drug's pipeline:
  Open Targets + ClinicalTrials.gov + openFDA + (skip SEC by default).

Resilient: per-drug try/except; logs failure reason; continues.
Summary at the end. Expects 10–30 min of runtime depending on CT.gov
response times.

Run:
  PYTHONPATH=. python scripts/batch_ingest.py                  # all 100
  PYTHONPATH=. python scripts/batch_ingest.py --limit 10       # first 10
  PYTHONPATH=. python scripts/batch_ingest.py --concurrency 3  # 3 parallel
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

from app.services.drug_ingest import DrugIngestSpec, ingest_drug_full


BATCH_FILE = Path(__file__).resolve().parents[2] / "data" / "curated" / "batch_drug_list.json"


class DrugResult:
    def __init__(self, spec: DrugIngestSpec) -> None:
        self.spec = spec
        self.ok = False
        self.report = None
        self.error: str | None = None
        self.seconds: float = 0.0

    def summary(self) -> str:
        if self.ok:
            r = self.report
            return (
                f"  ✔ {self.spec.generic_name:<30} {self.spec.chembl_id:<16} "
                f"tgts={r.target_count:>2}  inds={r.indication_count:>4}  "
                f"trials={r.trials_count:>4}  fda={r.regulatory_decisions_total:>3}  "
                f"({self.seconds:.1f}s)"
            )
        return f"  ✘ {self.spec.generic_name:<30} {self.spec.chembl_id:<16} FAIL: {self.error}"


async def ingest_one(spec: DrugIngestSpec, sem: asyncio.Semaphore) -> DrugResult:
    result = DrugResult(spec)
    async with sem:
        start = time.perf_counter()
        try:
            result.report = await ingest_drug_full(spec)
            result.ok = True
        except Exception as exc:  # noqa: BLE001 — surface every failure
            result.error = f"{type(exc).__name__}: {exc}"
        result.seconds = time.perf_counter() - start
    print(result.summary(), flush=True)
    return result


async def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--concurrency", type=int, default=3)
    args = parser.parse_args()

    drugs = json.loads(BATCH_FILE.read_text())["drugs"]
    if args.limit:
        drugs = drugs[: args.limit]

    print(f"batch ingest: {len(drugs)} drugs, concurrency={args.concurrency}")
    print("-" * 96)

    sem = asyncio.Semaphore(args.concurrency)
    specs = [
        DrugIngestSpec(
            chembl_id=d["chembl_id"],
            generic_name=d["generic_name"],
            originator_tickers=[],  # skip SEC in batch; hand-ingest for SEC step
            link_originator=False,
        )
        for d in drugs
    ]

    t0 = time.perf_counter()
    results = await asyncio.gather(*(ingest_one(s, sem) for s in specs))
    elapsed = time.perf_counter() - t0

    print("-" * 96)
    ok = [r for r in results if r.ok]
    fail = [r for r in results if not r.ok]
    print(f"done in {elapsed:.1f}s — {len(ok)}/{len(results)} ingested, {len(fail)} failed")
    if fail:
        print("\nfailures:")
        for r in fail:
            print(f"  {r.spec.chembl_id} / {r.spec.generic_name}: {r.error}")
    return 0 if len(fail) < len(results) // 10 else 1  # tolerate <10% failures


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
