"""GET /api/drugs/{id} — envelope shape + Humira smoke test."""

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
            pytest.skip("Humira not ingested — run scripts/ingest_adalimumab.py first")
        return drug.id


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_drug_returns_envelope(client: AsyncClient, humira_id: UUID) -> None:
    r = await client.get(f"/api/drugs/{humira_id}")
    assert r.status_code == 200
    body = r.json()

    assert set(body.keys()) == {"data", "meta", "related"}
    assert body["data"]["generic_name"] == "adalimumab"
    assert body["data"]["chembl_id"] == HUMIRA_CHEMBL_ID
    assert body["meta"]["entity_type"] == "drug"
    assert isinstance(body["meta"]["version"], int)


async def test_get_drug_related_chips_populated(client: AsyncClient, humira_id: UUID) -> None:
    r = await client.get(f"/api/drugs/{humira_id}")
    body = r.json()

    assert "targets" in body["related"]
    assert "indications" in body["related"]
    assert any("TNF" in (t.get("gene_symbol") or "") for t in body["related"]["targets"])
    assert len(body["related"]["indications"]) >= 10


async def test_get_drug_404_on_missing(client: AsyncClient) -> None:
    r = await client.get(f"/api/drugs/{uuid4()}")
    assert r.status_code == 404


async def test_get_drug_narrative_bilingual(client: AsyncClient, humira_id: UUID) -> None:
    r = await client.get(f"/api/drugs/{humira_id}")
    data = r.json()["data"]

    # Humira has curated narratives from P2-D0; both EN and ZH present.
    assert data["discovery_narrative"] and len(data["discovery_narrative"]) > 100
    assert data["discovery_narrative_zh"] and len(data["discovery_narrative_zh"]) > 30


async def test_health() -> None:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


# ── P3-D2: sub-endpoints ─────────────────────────────────────────────


async def test_get_drug_timeline(client: AsyncClient, humira_id: UUID) -> None:
    r = await client.get(f"/api/drugs/{humira_id}/timeline")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "event"
    assert body["meta"]["count"] >= 15  # Humira test: has_timeline
    dates = [e["event_date"] for e in body["data"] if e["event_date"]]
    assert dates == sorted(dates), "timeline must be date-ordered"
    # At least one causal link (Humira golden requirement)
    assert any(e["triggered_by"] is not None for e in body["data"])


async def test_get_drug_claims(client: AsyncClient, humira_id: UUID) -> None:
    r = await client.get(f"/api/drugs/{humira_id}/claims")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "claim"
    assert body["meta"]["count"] >= 5  # Humira golden: has_claims
    types = {c["claim_type"] for c in body["data"]}
    assert "verified_fact" in types or "attributed_analysis" in types


async def test_get_drug_lessons_human_reviewed_first(
    client: AsyncClient, humira_id: UUID
) -> None:
    r = await client.get(f"/api/drugs/{humira_id}/lessons")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["count"] >= 2  # Humira golden: has_lessons
    reviewed_flags = [l["human_reviewed"] for l in body["data"]]
    # All True values come before any False (human-reviewed first).
    if True in reviewed_flags and False in reviewed_flags:
        assert reviewed_flags.index(False) > reviewed_flags.index(True)


async def test_subroutes_404_on_missing(client: AsyncClient) -> None:
    bogus = uuid4()
    for path in (
        f"/api/drugs/{bogus}/timeline",
        f"/api/drugs/{bogus}/claims",
        f"/api/drugs/{bogus}/lessons",
        f"/api/drugs/{bogus}/patents",
        f"/api/drugs/{bogus}/regulatory-decisions",
    ):
        r = await client.get(path)
        assert r.status_code == 404, path


async def test_get_drug_patents(client: AsyncClient, humira_id: UUID) -> None:
    r = await client.get(f"/api/drugs/{humira_id}/patents")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "patent"
    assert body["meta"]["count"] >= 1  # core patent seeded curated
    numbers = {p["patent_number"] for p in body["data"]}
    assert "6090382" in numbers  # Humira core patent


async def test_get_drug_patents_filter_by_register(client: AsyncClient, humira_id: UUID) -> None:
    r = await client.get(f"/api/drugs/{humira_id}/patents?register=uspto_manual")
    assert r.status_code == 200
    body = r.json()
    assert all(p["source_register"] == "uspto_manual" for p in body["data"])


async def test_get_drug_regulatory_decisions(client: AsyncClient, humira_id: UUID) -> None:
    r = await client.get(f"/api/drugs/{humira_id}/regulatory-decisions")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "regulatory_decision"
    assert body["meta"]["count"] >= 5  # Humira golden: regulatory_decisions_count
    dates = [d["decision_date"] for d in body["data"] if d["decision_date"]]
    assert dates == sorted(dates), "regulatory decisions must be date-ordered"


async def test_get_drug_regulatory_decisions_jurisdiction_filter(
    client: AsyncClient, humira_id: UUID
) -> None:
    r = await client.get(f"/api/drugs/{humira_id}/regulatory-decisions?jurisdiction=FDA")
    assert r.status_code == 200
    body = r.json()
    assert all(d["jurisdiction"] == "FDA" for d in body["data"])
