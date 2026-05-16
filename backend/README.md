# BioGraph backend

FastAPI + SQLAlchemy (async) + PostgreSQL + Alembic backend for the BioGraph
knowledge graph prototype.

## Prerequisites

- **Docker runtime** — Colima (recommended; `brew install colima docker docker-compose`) or Docker Desktop.
- **Python 3.14** — pinned in `../.python-version`.

## First-time setup

From the repo root:

```bash
# 1. Boot services (db, search, redis)
colima start            # skip if Docker Desktop is running
docker compose up -d
docker compose ps       # expect three "healthy" services

# 2. Env
cp .env.example .env    # dev defaults already work against docker-compose

# 3. Backend venv + deps
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 4. Schema
alembic upgrade head    # creates 18 tables + entity_relationships VIEW

# 5. Seed - pick one
PYTHONPATH=. python scripts/ingest_adalimumab.py    # hits live Open Targets
#   OR
PYTHONPATH=. python scripts/seed_phase_0.py         # replays fixture, no network
```

## Daily work

```bash
# From backend/ with .venv active:
./.venv/bin/pytest -v                                 # full suite
./.venv/bin/pytest tests/test_golden.py -v            # CI gate (Humira + NASH)
./.venv/bin/pytest -m live -v                         # live external-API tests
PYTHONPATH=. python scripts/qa_check.py --phase 0     # fixture/data QA check
```

## Project layout

```
backend/
├── alembic.ini                 # sync driver; env.py loads URL from .env
├── app/
│   ├── config.py               # pydantic-settings Settings (one instance, module-level)
│   ├── db.py                   # async engine + get_session context manager
│   ├── models/                 # graph entities + junctions + bilingual narrative mixin
│   ├── ingestion/              # BaseIngester ABC + per-source ingesters
│   ├── services/               # Domain logic — upsert_drug_from_open_targets, etc.
│   └── api/                    # FastAPI routers
├── migrations/versions/        # Alembic migrations
├── scripts/
│   ├── ingest_adalimumab.py    # live API ingest example
│   ├── seed_phase_0.py         # offline fixture seed
│   └── qa_check.py             # data quality checker
├── tests/
│   ├── test_models_invariants.py  # bilingual-field invariant checks
│   ├── test_ingestion/            # per-source ingester unit tests
│   ├── test_humira_golden.py      # Humira regression checks
│   ├── test_nash_landscape.py     # landscape regression checks
│   ├── test_golden.py             # smoke orchestrator for CI gate
│   └── fixtures/                  # committed golden raw payloads
├── pyproject.toml              # pytest config
└── requirements.txt            # pinned deps (20)
```

## Common gotchas

- **Running `pytest` outside `.venv` picks up system Python** — always use `./.venv/bin/pytest` or `source .venv/bin/activate` first.
- **`PYTHONPATH=.`** needed for `python scripts/...` because `app/` is not an installed package.
- **Alembic round-trip** (downgrade -> upgrade) works only because `downgrade()` explicitly drops the 3 ENUM types (PostgreSQL doesn't auto-drop them with columns).
- **Live tests are `-m live` gated** and deselected by default. Run them sparingly; they hit Open Targets / PubMed / etc.

## Refreshing the Open Targets fixture

When Open Targets' schema drifts, regenerate the cached fixture:

```bash
# Hit live API and re-seed
PYTHONPATH=. python scripts/ingest_adalimumab.py

# Copy raw cache to committed test fixture
cp ../data/raw/open_targets/CHEMBL1201580.json tests/fixtures/open_targets_CHEMBL1201580.json

# Verify unit tests still pass
./.venv/bin/pytest tests/test_ingestion/ -v
```

Commit the fixture change; CI reads from `tests/fixtures/`.
