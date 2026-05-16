# BioGraph frontend

Next.js App Router frontend for the BioGraph knowledge graph prototype.

## Setup

```bash
cp .env.example .env.local
npm install
npm run dev
```

Open http://localhost:3000.

The frontend expects the FastAPI backend at `NEXT_PUBLIC_BIOGRAPH_API_URL`.
For local development, keep the default `http://localhost:8000`.

## Useful Commands

```bash
npm run dev
npm run build
npm run lint
```

## Main Routes

- `/` - searchable landing page
- `/search` - combined entity search
- `/explore` - graph explorer
- `/drug/[id]`, `/target/[id]`, `/company/[id]`, `/indication/[id]` - entity detail pages
- `/landscape/[slug]` - curated landscape pages
