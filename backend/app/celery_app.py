"""Celery app — Redis broker + Beat schedule for daily ingestion refresh.

Worker:
    cd backend && source .venv/bin/activate
    celery -A app.celery_app worker --loglevel=info --concurrency=2

Beat scheduler (separate process):
    celery -A app.celery_app beat --loglevel=info

Docker-compose wires both as long-running services; the web API is
unaffected by Celery state.

Tasks are defined in app.tasks.* and discovered via `include=` below.
"""

from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.config import settings

celery_app = Celery(
    "biograph",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["app.tasks.ingestion"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    # A single refresh run takes ~4 minutes at concurrency 4. Kill a task
    # that exceeds 20 min — something upstream is stuck (CT.gov time-out,
    # DB lock) and a retry has better odds than waiting.
    task_time_limit=20 * 60,
    task_soft_time_limit=18 * 60,
    # Per-task acks late so a worker crash re-queues, not loses.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

celery_app.conf.beat_schedule = {
    # Daily full drug refresh at 02:00 UTC — low-traffic window for
    # Open Targets + CT.gov + openFDA.
    "daily-refresh-all-drugs": {
        "task": "app.tasks.ingestion.refresh_all_drugs",
        "schedule": crontab(hour=2, minute=0),
        "options": {"expires": 60 * 60},  # drop if not picked up within 1hr
    },
    # Search index rebuild 30 min after the refresh completes.
    "daily-rebuild-search-index": {
        "task": "app.tasks.ingestion.refresh_search_index",
        "schedule": crontab(hour=2, minute=30),
        "options": {"expires": 60 * 60},
    },
}
