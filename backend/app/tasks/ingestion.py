"""Celery tasks for scheduled ingestion refresh.

All ingest code is async; each task wraps with `asyncio.run(...)`. That
gives each task a fresh event loop (no cross-task pool reuse).

Tasks (invoked by Beat schedule in app.celery_app):
  refresh_all_drugs  — re-runs ingest_drug_full over every existing
                       Drug by chembl_id; idempotent upserts update
                       trials, regulatory decisions, targets in place.
  refresh_single_drug — manual-trigger variant (admin UI / CLI).
  refresh_search_index — rebuilds the Meilisearch entities index.
"""

from __future__ import annotations

import asyncio
import logging
import time

from celery import shared_task
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Drug
from app.services.drug_ingest import DrugIngestSpec, ingest_drug_full

log = logging.getLogger(__name__)


@shared_task(
    bind=True,
    name="app.tasks.ingestion.refresh_all_drugs",
    autoretry_for=(Exception,),
    retry_backoff=60,
    retry_backoff_max=600,
    retry_jitter=True,
    max_retries=2,
    acks_late=True,
)
def refresh_all_drugs(self, concurrency: int = 4) -> dict:
    """Re-ingest every Drug row by chembl_id. Returns summary counts."""
    specs = _load_drug_specs()
    log.info("refresh_all_drugs: %d drugs, concurrency=%d", len(specs), concurrency)

    t0 = time.perf_counter()
    ok, failed = asyncio.run(_run_refresh(specs, concurrency))
    elapsed = time.perf_counter() - t0

    summary = {
        "drugs_total": len(specs),
        "drugs_ok": len(ok),
        "drugs_failed": len(failed),
        "elapsed_seconds": round(elapsed, 1),
        "failures": failed[:20],  # cap for log readability
    }
    log.info("refresh_all_drugs summary: %s", summary)
    return summary


@shared_task(
    bind=True,
    name="app.tasks.ingestion.refresh_single_drug",
    autoretry_for=(Exception,),
    retry_backoff=30,
    max_retries=3,
    acks_late=True,
)
def refresh_single_drug(self, chembl_id: str) -> dict:
    """Admin-trigger refresh of a single drug. Idempotent."""
    specs = [s for s in _load_drug_specs() if s.chembl_id == chembl_id]
    if not specs:
        raise ValueError(f"no Drug row with chembl_id={chembl_id}")
    asyncio.run(ingest_drug_full(specs[0]))
    return {"chembl_id": chembl_id, "status": "ok"}


@shared_task(
    bind=True,
    name="app.tasks.ingestion.refresh_search_index",
    acks_late=True,
)
def refresh_search_index(self) -> dict:
    """Drop and rebuild the Meilisearch entities index from Postgres."""
    from app.search import reindex_all_sync, reset_index

    reset_index()
    engine = create_engine(settings.database_url_sync)
    with Session(engine) as session:
        counts = reindex_all_sync(session)
    log.info("refresh_search_index counts: %s", counts)
    return counts


# ── helpers ──────────────────────────────────────────────────────────


def _load_drug_specs() -> list[DrugIngestSpec]:
    """Pull (chembl_id, generic_name) for every existing Drug row."""
    engine = create_engine(settings.database_url_sync)
    with Session(engine) as s:
        rows = s.execute(
            select(Drug.chembl_id, Drug.generic_name).where(Drug.chembl_id.is_not(None))
        ).all()
    return [
        DrugIngestSpec(chembl_id=cid, generic_name=name, link_originator=False)
        for cid, name in rows
        if cid and name
    ]


async def _run_refresh(
    specs: list[DrugIngestSpec], concurrency: int
) -> tuple[list[str], list[dict]]:
    sem = asyncio.Semaphore(concurrency)
    ok: list[str] = []
    failed: list[dict] = []

    async def one(spec: DrugIngestSpec) -> None:
        async with sem:
            try:
                await ingest_drug_full(spec)
                ok.append(spec.chembl_id)
            except Exception as exc:  # noqa: BLE001 — record per-drug failure, continue
                failed.append(
                    {"chembl_id": spec.chembl_id, "error": f"{type(exc).__name__}: {exc}"}
                )

    await asyncio.gather(*(one(s) for s in specs))
    return ok, failed
