"""Alembic migration round-trip regression (D-012).

Purpose: prevent D-010-class regressions where alembic autogen's
"detected removed index" false positives silently bake `op.drop_index`
calls into future migrations, only surfacing when a full downgrade /
upgrade cycle runs.

What it does:
  1. Create a disposable Postgres database `biograph_roundtrip_<pid>`
  2. Point alembic at it via DATABASE_URL / DATABASE_URL_SYNC overrides
  3. `alembic upgrade head` → `downgrade base` → `upgrade head`
  4. Assert specific indexes + the `entity_relationships` VIEW still
     exist at the end

Skipped by default (heavy: spins up migrations 15+ times). Run with:
    pytest tests/test_migration_roundtrip.py -m integration -v

Requires: the local docker-compose Postgres (biograph-db) reachable at
DATABASE_URL_SYNC's host, and the connecting user to have CREATE /
DROP DATABASE privileges (the `biograph` user does by default).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine, text

from app.config import settings

pytestmark = pytest.mark.integration

BACKEND_DIR = Path(__file__).resolve().parents[1]

# Invoke alembic via the current interpreter rather than relying on PATH —
# works whether you `pytest` from the venv activated or raw.
ALEMBIC_CMD = [sys.executable, "-m", "alembic"]

# Indexes + views that D-010 proved can get silently dropped. Names match
# migrations/versions/84c8d1ea439b_phase_1_day7_merge_conflicts_table_rd_.py.
REQUIRED_INDEXES = {
    "uq_regulatory_decisions_app_sub",
    "ix_merge_conflicts_entity",
    "ix_merge_conflicts_field",
    "ix_merge_conflicts_detected",
}
REQUIRED_VIEWS = {
    "entity_relationships",
}


def _roundtrip_db_name() -> str:
    return f"biograph_roundtrip_{os.getpid()}"


def _swap_db(dsn: str, new_name: str) -> str:
    """Return the DSN rewritten to point at `new_name`."""
    parts = urlparse(dsn)
    # urlparse puts the database name in `.path` (leading slash).
    new_path = f"/{new_name}"
    return parts._replace(path=new_path).geturl()


@pytest.fixture
def disposable_db() -> tuple[str, str]:
    """Create and yield (async_url, sync_url) for a fresh empty database.

    The admin connection reaches the default `postgres` database on the
    same host using the current DATABASE_URL_SYNC user; this user is a
    superuser in the docker-compose setup.
    """
    db_name = _roundtrip_db_name()
    admin_sync = _swap_db(settings.database_url_sync, "postgres")
    admin_engine = create_engine(admin_sync, isolation_level="AUTOCOMMIT")

    with admin_engine.connect() as c:
        c.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        c.execute(text(f'CREATE DATABASE "{db_name}"'))

    try:
        yield (
            _swap_db(settings.database_url, db_name),
            _swap_db(settings.database_url_sync, db_name),
        )
    finally:
        with admin_engine.connect() as c:
            # Disconnect anyone still attached, then drop.
            c.execute(
                text(
                    "SELECT pg_terminate_backend(pid) "
                    "FROM pg_stat_activity "
                    "WHERE datname = :n AND pid <> pg_backend_pid()"
                ),
                {"n": db_name},
            )
            c.execute(text(f'DROP DATABASE IF EXISTS "{db_name}"'))
        admin_engine.dispose()


def _run_alembic(cmd: list[str], env_overrides: dict[str, str]) -> None:
    env = {**os.environ, **env_overrides}
    result = subprocess.run(
        [*ALEMBIC_CMD, *cmd],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        pytest.fail(
            f"alembic {' '.join(cmd)} failed: "
            f"stdout={result.stdout!r} stderr={result.stderr!r}"
        )


def test_round_trip_preserves_indexes_and_views(
    disposable_db: tuple[str, str],
) -> None:
    async_url, sync_url = disposable_db
    env = {"DATABASE_URL": async_url, "DATABASE_URL_SYNC": sync_url}

    _run_alembic(["upgrade", "head"], env)
    _run_alembic(["downgrade", "base"], env)
    _run_alembic(["upgrade", "head"], env)

    engine = create_engine(sync_url)
    try:
        with engine.connect() as c:
            index_names = {
                row[0]
                for row in c.execute(
                    text(
                        "SELECT indexname FROM pg_indexes "
                        "WHERE schemaname = 'public'"
                    )
                ).all()
            }
            view_names = {
                row[0]
                for row in c.execute(
                    text(
                        "SELECT viewname FROM pg_views "
                        "WHERE schemaname = 'public'"
                    )
                ).all()
            }
    finally:
        engine.dispose()

    missing_indexes = REQUIRED_INDEXES - index_names
    missing_views = REQUIRED_VIEWS - view_names
    assert not missing_indexes, f"indexes missing after round-trip: {missing_indexes}"
    assert not missing_views, f"views missing after round-trip: {missing_views}"
