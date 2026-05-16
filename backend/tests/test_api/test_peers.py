"""Peer entity endpoints — target/company/indication detail.

Each test reaches an entity via Humira's relationships: Humira → TNF,
Humira's originator company, Humira → rheumatoid arthritis indication.
"""

from uuid import UUID, uuid4

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.main import app
from app.models import Company, Drug, Indication, Target

HUMIRA_CHEMBL_ID = "CHEMBL1201580"
_sync_engine = create_engine(settings.database_url_sync, pool_pre_ping=True)


def _humira() -> Drug | None:
    with Session(_sync_engine) as s:
        return s.scalar(select(Drug).where(Drug.chembl_id == HUMIRA_CHEMBL_ID))


@pytest.fixture
def tnf_target_id() -> UUID:
    with Session(_sync_engine) as s:
        drug = _humira()
        if drug is None:
            pytest.skip("Humira not ingested")
        s.add(drug)
        tnf = next((t for t in drug.targets if "TNF" in (t.gene_symbol or "")), None)
        if tnf is None:
            pytest.skip("Humira has no TNF target linked")
        return tnf.id


@pytest.fixture
def humira_indication_id() -> UUID:
    with Session(_sync_engine) as s:
        drug = _humira()
        if drug is None:
            pytest.skip("Humira not ingested")
        s.add(drug)
        if not drug.indications:
            pytest.skip("Humira has no indications linked")
        return drug.indications[0].id


@pytest.fixture
def any_company_id() -> UUID:
    with Session(_sync_engine) as s:
        company = s.scalar(select(Company).limit(1))
        if company is None:
            pytest.skip("No companies ingested")
        return company.id


@pytest.fixture
async def client() -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


async def test_get_target(client: AsyncClient, tnf_target_id: UUID) -> None:
    r = await client.get(f"/api/targets/{tnf_target_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "target"
    assert "TNF" in (body["data"]["gene_symbol"] or "")
    assert any(d["generic_name"] == "adalimumab" for d in body["related"]["drugs"])


async def test_get_company(client: AsyncClient, any_company_id: UUID) -> None:
    r = await client.get(f"/api/companies/{any_company_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "company"
    assert body["data"]["name"]
    assert "drugs" in body["related"]


async def test_get_indication(client: AsyncClient, humira_indication_id: UUID) -> None:
    r = await client.get(f"/api/indications/{humira_indication_id}")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "indication"
    assert body["data"]["name"]
    assert any(d["generic_name"] == "adalimumab" for d in body["related"]["drugs"])


async def test_peers_404(client: AsyncClient) -> None:
    bogus = uuid4()
    for path in (
        f"/api/targets/{bogus}",
        f"/api/companies/{bogus}",
        f"/api/indications/{bogus}",
        f"/api/targets/{bogus}/drugs",
        f"/api/companies/{bogus}/pipeline",
        f"/api/companies/{bogus}/deals",
    ):
        r = await client.get(path)
        assert r.status_code == 404, path


async def test_target_drugs_list(client: AsyncClient, tnf_target_id: UUID) -> None:
    r = await client.get(f"/api/targets/{tnf_target_id}/drugs")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "drug"
    assert any(d["generic_name"] == "adalimumab" for d in body["data"])


async def test_company_pipeline(client: AsyncClient, any_company_id: UUID) -> None:
    r = await client.get(f"/api/companies/{any_company_id}/pipeline")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "drug"
    # May be empty for companies without originated drugs — just shape-check.
    assert isinstance(body["data"], list)


async def test_company_deals_returns_list(client: AsyncClient, any_company_id: UUID) -> None:
    r = await client.get(f"/api/companies/{any_company_id}/deals")
    assert r.status_code == 200
    body = r.json()
    assert body["meta"]["entity_type"] == "deal"
    assert isinstance(body["data"], list)
