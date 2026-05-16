# BioGraph backend image — serves both the FastAPI app and Celery
# worker/beat. Target differs by CMD override at runtime.
#
# Build context must be the REPO ROOT (not backend/) so COPY can reach
# both backend/ and data/. Canonical build:
#
#   docker build -f backend/Dockerfile -t biograph-backend .
#
# Runtime selection:
#   uvicorn app.main:app --host 0.0.0.0            # API server (default)
#   celery -A app.celery_app worker -l info        # task worker
#   celery -A app.celery_app beat -l info          # scheduler
#
# Multi-stage: wheel build in one image, slim runtime in the next.

# ── Builder ───────────────────────────────────────────────────────────
FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip wheel --wheel-dir /wheels -r requirements.txt

# ── Runtime ──────────────────────────────────────────────────────────
FROM python:3.14-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PYTHONPATH=/app

WORKDIR /app

RUN groupadd --system biograph && useradd --system --gid biograph biograph

COPY --from=builder /wheels /wheels
COPY backend/requirements.txt .
RUN pip install --no-index --find-links=/wheels -r requirements.txt \
    && rm -rf /wheels

# Backend source
COPY backend/app/        app/
COPY backend/migrations/ migrations/
COPY backend/scripts/    scripts/
COPY backend/alembic.ini ./

# Curated data directory lives at repo-root/data; landscape engine and
# curated loaders read from it at request time.
COPY data/ /app/data/

RUN chown -R biograph:biograph /app
USER biograph

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers"]
