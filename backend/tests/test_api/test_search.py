"""Global /api/search — Meilisearch-backed.

Module-skips if the Meilisearch server isn't reachable. Seeds the index
once per session using the live Postgres data (same data test_drugs uses).
"""

import time

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import meilisearch
from app.config import settings
from app.main import app
from app.search import ENTITIES_INDEX, client, reindex_all_sync, reset_index


def _meili_up() -> bool:
    try:
        health = client().health()
        return bool(health and health.get("status") == "available")
    except Exception:
        return False


if not _meili_up():
    pytest.skip(
        "Meilisearch not reachable at {}; run `docker compose up -d search`".format(
            settings.meili_url
        ),
        allow_module_level=True,
    )


@pytest.fixture(scope="module", autouse=True)
def _seed_index() -> None:
    reset_index()
    engine = create_engine(settings.database_url_sync)
    with Session(engine) as s:
        reindex_all_sync(s)
    # Meili indexes asynchronously; poll for "all tasks done" a few times.
    idx = client().index(ENTITIES_INDEX)
    for _ in range(30):
        stats = idx.get_stats()
        if stats.number_of_documents > 0 and not stats.is_indexing:
            return
        time.sleep(0.2)


@pytest.fixture
async def http_client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_search_humira_english(http_client: AsyncClient) -> None:
    r = await http_client.get("/api/search?q=humira")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "search_result"
    drugs = [h for h in body["data"] if h["entity_type"] == "drug"]
    assert any(d["display_name"] == "adalimumab" for d in drugs)


async def test_search_by_generic_name(http_client: AsyncClient) -> None:
    r = await http_client.get("/api/search?q=adalimumab")
    assert r.status_code == 200
    body = r.json()
    assert any(h["display_name"] == "adalimumab" for h in body["data"])


async def test_search_type_filter(http_client: AsyncClient) -> None:
    r = await http_client.get("/api/search?q=adalimumab&type=drug")
    assert r.status_code == 200
    body = r.json()
    assert all(h["entity_type"] == "drug" for h in body["data"])
    assert len(body["data"]) >= 1


async def test_search_unknown_type_400(http_client: AsyncClient) -> None:
    r = await http_client.get("/api/search?q=adalimumab&type=drogue")
    assert r.status_code == 400


async def test_search_empty_query_422(http_client: AsyncClient) -> None:
    r = await http_client.get("/api/search?q=")
    assert r.status_code == 422


async def test_search_results_carry_link(http_client: AsyncClient) -> None:
    r = await http_client.get("/api/search?q=adalimumab&type=drug")
    body = r.json()
    first = body["data"][0]
    assert first["link"].startswith("/api/drugs/")
