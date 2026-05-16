"""FastAPI app entry point.

Run locally:
    cd backend && source .venv/bin/activate
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.api.companies import router as companies_router
from app.api.drugs import router as drugs_router
from app.api.graph import router as graph_router
from app.api.indications import router as indications_router
from app.api.landscape import router as landscape_router
from app.api.search import router as search_router
from app.api.targets import router as targets_router

app = FastAPI(title="BioGraph API", version="0.1.0")

# Next.js SearchBar is a client component, so the browser hits the API
# directly. Origins are env-driven via CORS_ORIGINS (comma-separated);
# defaults to localhost dev ports. Prod deploys must override — e.g.
# CORS_ORIGINS="https://biograph.app,https://www.biograph.app".
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_origin_regex=settings.cors_origin_regex or None,
    allow_methods=["GET"],
    allow_headers=["*"],
)

app.include_router(drugs_router)
app.include_router(targets_router)
app.include_router(companies_router)
app.include_router(indications_router)
app.include_router(graph_router)
app.include_router(search_router)
app.include_router(landscape_router)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
