#!/usr/bin/env bash
# Seed a freshly-migrated prod database with the v1 dataset.
#
# The script reads DATABASE_URL / DATABASE_URL_SYNC / MEILI_URL /
# MEILI_MASTER_KEY from the current shell — export them to point at
# prod before running:
#
#   export DATABASE_URL='postgresql+asyncpg://…neon.tech/biograph?ssl=require'
#   export DATABASE_URL_SYNC='postgresql+psycopg2://…neon.tech/biograph?sslmode=require'
#   export MEILI_URL='https://ms-xxxxx.meilisearch.io'
#   export MEILI_MASTER_KEY='…'
#   bash backend/scripts/seed_prod.sh
#
# Expect ~6-8 min wall clock against a fresh DB (3 hand-ingests +
# 500-drug batch + Meili rebuild). All steps idempotent — safe to re-run.

set -euo pipefail

here="$(cd "$(dirname "$0")" && pwd)"
cd "$here/.."

if [[ ! -x .venv/bin/python ]]; then
  echo "✘ No backend/.venv/bin/python. Run \`python -m venv .venv && pip install -r requirements.txt\` first." >&2
  exit 1
fi

: "${DATABASE_URL:?DATABASE_URL must be set (asyncpg DSN)}"
: "${DATABASE_URL_SYNC:?DATABASE_URL_SYNC must be set (psycopg2 DSN)}"
: "${MEILI_URL:?MEILI_URL must be set}"
: "${MEILI_MASTER_KEY:?MEILI_MASTER_KEY must be set}"

host="$(.venv/bin/python -c "from urllib.parse import urlparse; import os; print(urlparse(os.environ['DATABASE_URL_SYNC'].replace('postgresql+psycopg2', 'postgresql')).hostname)")"
echo "→ seeding against DB host: $host"
echo "→ Meili: $MEILI_URL"
read -r -p "Proceed? [y/N] " reply
if [[ "${reply:-}" != "y" && "${reply:-}" != "Y" ]]; then
  echo "abort"; exit 1
fi

export PYTHONPATH=.

echo "=== 1/5  alembic upgrade head ==="
.venv/bin/alembic upgrade head

echo "=== 2/5  3 golden entities (Humira, Keytruda, Ozempic) ==="
.venv/bin/python scripts/ingest_adalimumab.py
.venv/bin/python scripts/ingest_keytruda.py
.venv/bin/python scripts/ingest_ozempic.py

echo "=== 3/5  500-drug batch ==="
.venv/bin/python scripts/batch_ingest.py --concurrency 4

echo "=== 4/5  Meilisearch index rebuild ==="
.venv/bin/python scripts/build_search_index.py

echo "=== 5/5  post-seed verification ==="
.venv/bin/python - <<'PY'
from app.config import settings
from sqlalchemy import create_engine, text

eng = create_engine(settings.database_url_sync)
with eng.connect() as c:
    for tbl in ("drugs", "targets", "indications", "clinical_trials",
                "regulatory_decisions", "companies"):
        n = c.execute(text(f"SELECT count(*) FROM {tbl}")).scalar()
        print(f"  {tbl:<22} {n:>8}")
PY

echo "✔ seed complete — verify Humira / NASH landscape from the frontend"
