# biograph

> Local biopharma knowledge graph prototype for drugs, targets, companies, indications, clinical trials, patents, regulatory decisions, and evidence-linked claims.

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg) ![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-green.svg) ![Next.js](https://img.shields.io/badge/Next.js-App_Router-black.svg)

## What it does

| Metric | Value |
|--------|-------|
| Entity types | 12 (Drug, Target, Company, Indication, ClinicalTrial, RegulatoryDecision, Patent, Event, Article, Claim, Lesson, Deal) |
| Knowledge objects | Claim (evidence-linked assertions) + Lesson (cross-entity patterns with limitations) |
| Language | Bilingual fields and query-parameter switching |
| Search | Meilisearch-backed full-text with alias and landscape slug matching |
| Graph | D3 force-directed knowledge graph with pan/zoom, type coloring, and entity filters |
| Data provenance | Per-field `field_provenance` dict + `last_verified_at` timestamp on every entity |

## Why it exists

Biopharma intelligence is scattered across DrugBank, ChEMBL, ClinicalTrials.gov, Orange Book, SEC filings, and primary literature. BioGraph shows one way to compile public sources into a navigable knowledge graph with provenance tracking and structured Claim/Lesson objects.

## Architecture

**Backend:** Python + FastAPI + SQLAlchemy (async) + Alembic + Pydantic Settings + Uvicorn. PostgreSQL primary database with Meilisearch for search and Redis + Celery for background refresh.

**Frontend:** Next.js App Router + React + TypeScript + Tailwind CSS v4 + D3 + Recharts. Shared layout with search bar, language toggle (EN/ZH), and theme toggle.

**Data:** PostgreSQL via `postgresql+asyncpg`. Local infra in `docker-compose.yml` (Postgres 16, Meilisearch v1.6, Redis 7). Curated landscape pages backed by YAML files in `data/landscapes/`.

## Features

- Bilingual CN/EN content switching via header toggle and `?lang=zh` parameter
- Entity search combining Meilisearch hits with curated landscape slug and alias matches (including Chinese names)
- Knowledge graph explorer at `/explore` with D3 force graph, pan/zoom, type coloring, and entity filters
- Per-entity mini graphs on detail pages
- Landscape analysis pages backed by curated YAML (e.g., Alzheimer's pipeline landscape)
- Theme toggle persisted in localStorage
- Entity detail pages for drugs, targets, companies, and indications with timelines, claims, lessons, metrics

## Quick start

```bash
# Start local infrastructure
docker compose up -d

# Backend API
cd backend && python3 -m venv .venv
source .venv/bin/activate && pip install -r requirements.txt
alembic upgrade head
PYTHONPATH=. python scripts/seed_phase_0.py  # seed fixture data
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend && cp .env.example .env.local
npm install && npm run dev
```

Then open:

- Frontend: http://localhost:3000
- API docs: http://localhost:8000/docs
- Health check: http://localhost:8000/health

## Schema overview

12 entity types with full provenance tracking. Core knowledge objects:

- **Claim** — evidence-linked assertion extracted from an Article, with claim type, confidence, and entity mentions
- **Lesson** — cross-entity pattern with key evidence, limitations, applicable contexts, and human review status
- **MergeConflict** — explicit resolution record when sources disagree on a field value

See the full schema definitions in the source code under `backend/app/models/`.

## License

MIT. See [LICENSE](LICENSE).
