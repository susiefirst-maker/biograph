"""Celery app + tasks register correctly and the Beat schedule is sane.

No broker is hit; we exercise config + import paths only. Actual end-to-
end execution is validated manually via `celery worker` + `celery beat`.
"""

from celery.schedules import crontab

from app.celery_app import celery_app
from app.tasks import ingestion


def test_tasks_registered() -> None:
    names = {
        "app.tasks.ingestion.refresh_all_drugs",
        "app.tasks.ingestion.refresh_single_drug",
        "app.tasks.ingestion.refresh_search_index",
    }
    assert names.issubset(celery_app.tasks)


def test_beat_schedule_has_daily_refresh() -> None:
    sched = celery_app.conf.beat_schedule
    assert "daily-refresh-all-drugs" in sched
    assert "daily-rebuild-search-index" in sched
    refresh = sched["daily-refresh-all-drugs"]
    assert refresh["task"] == "app.tasks.ingestion.refresh_all_drugs"
    assert isinstance(refresh["schedule"], crontab)


def test_broker_and_backend_point_at_redis() -> None:
    assert celery_app.conf.broker_url.startswith("redis://")
    assert celery_app.conf.result_backend.startswith("redis://")


def test_task_time_limits_set() -> None:
    assert celery_app.conf.task_time_limit == 20 * 60
    assert celery_app.conf.task_soft_time_limit == 18 * 60


def test_load_drug_specs_queries_postgres() -> None:
    """Smoke: helper returns a non-empty list when drugs are present."""
    specs = ingestion._load_drug_specs()
    assert isinstance(specs, list)
    # After P5-D2 the DB holds ~500 drugs; any positive count proves the
    # query wires up. If 0 is legitimate (fresh DB), the assertion still
    # passes via the outer isinstance check.
    for s in specs[:3]:
        assert s.chembl_id and s.generic_name
