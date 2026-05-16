"""Graph neighbor endpoint — depth-1 and depth-2 over entity_relationships."""

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.main import app
from app.models import Drug

HUMIRA_CHEMBL_ID = "CHEMBL1201580"
_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


@pytest.fixture
def humira_id() -> UUID:
    with Session(_sync_engine) as s:
        drug = s.scalar(select(Drug).where(Drug.chembl_id == HUMIRA_CHEMBL_ID))
        if drug is None:
            pytest.skip("Humira not ingested")
        return drug.id


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_neighbors_depth1_includes_target_and_indications(
    client: AsyncClient, humira_id: UUID
) -> None:
    r = await client.get(f"/api/graph/neighbors/drug/{humira_id}?depth=1")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "graph"
    assert body["meta"]["root_type"] == "drug"
    assert body["meta"]["depth"] == 1

    types = {n["type"] for n in body["data"]["nodes"]}
    assert "target" in types
    assert "indication" in types
    # The root itself is a node at distance 0
    assert body["data"]["source"]["distance"] == 0
    assert body["data"]["source"]["type"] == "drug"

    # Edges are outbound from the root
    edges = body["data"]["edges"]
    assert len(edges) > 0
    assert all(e["source_type"] == "drug" for e in edges)


async def test_neighbors_depth2_reaches_further(
    client: AsyncClient, humira_id: UUID
) -> None:
    r1 = await client.get(f"/api/graph/neighbors/drug/{humira_id}?depth=1")
    r2 = await client.get(f"/api/graph/neighbors/drug/{humira_id}?depth=2")
    assert r2.status_code == 200
    # Depth-2 must reach at least as many nodes/edges as depth-1.
    assert r2.json()["meta"]["node_count"] >= r1.json()["meta"]["node_count"]
    assert r2.json()["meta"]["edge_count"] >= r1.json()["meta"]["edge_count"]


async def test_neighbors_unknown_type_400(client: AsyncClient) -> None:
    r = await client.get(f"/api/graph/neighbors/drogue/{uuid4()}?depth=1")
    assert r.status_code == 400


async def test_neighbors_missing_entity_404(client: AsyncClient) -> None:
    r = await client.get(f"/api/graph/neighbors/drug/{uuid4()}?depth=1")
    assert r.status_code == 404


async def test_neighbors_depth_clamped(client: AsyncClient, humira_id: UUID) -> None:
    # depth=0 and depth=3 rejected by FastAPI Query validator.
    for bad in (0, 3):
        r = await client.get(f"/api/graph/neighbors/drug/{humira_id}?depth={bad}")
        assert r.status_code == 422, bad
