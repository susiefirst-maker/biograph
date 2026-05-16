"""SEC EDGAR ingester unit tests (fixture-based, no network)."""

import json
from pathlib import Path

import pytest

from app.ingestion.sec_edgar import (
    SECEdgarIngester,
    _extract_annual_revenue,
)


FIXTURE_DIR = Path(__file__).parent.parent / "fixtures"
ABBV_FIXTURE = FIXTURE_DIR / "sec_abbv_raw.json"


@pytest.fixture
def abbv_raw() -> dict:
    assert ABBV_FIXTURE.exists()
    return json.loads(ABBV_FIXTURE.read_text())


def test_normalize_abbv(abbv_raw: dict) -> None:
    ing = SECEdgarIngester()
    normalized = ing.normalize(abbv_raw)

    company = normalized["company"]
    assert company["sec_cik"] == "1551152"
    assert company["ticker"] == "ABBV"
    assert "AbbVie" in company["name"]

    revenues = normalized["annual_revenues"]
    assert len(revenues) >= 10, f"expected ≥10 FY revenue entries, got {len(revenues)}"

    # AbbVie's Humira-peak year 2021 — total Company revenue was ~$56.2B
    y2021 = [r for r in revenues if r["year"] == 2021]
    assert y2021, "no 2021 entries"
    assert max(r["usd"] for r in y2021) > 50_000_000_000


def test_normalize_empty_ticker_entry() -> None:
    ing = SECEdgarIngester()
    normalized = ing.normalize({"ticker_entry": None, "companyfacts": None})
    assert normalized == {}


def test_validate_flags_missing_cik() -> None:
    ing = SECEdgarIngester()
    errors = ing.validate({"company": {"sec_cik": None, "ticker": "X", "name": "Y"}})
    assert any("sec_cik" in e for e in errors)


def test_validate_flags_missing_ticker(abbv_raw: dict) -> None:
    ing = SECEdgarIngester()
    normalized = ing.normalize(abbv_raw)
    normalized["company"]["ticker"] = ""
    errors = ing.validate(normalized)
    assert any("ticker" in e for e in errors)


def test_validate_flags_empty_payload() -> None:
    assert SECEdgarIngester().validate({}) == ["SEC EDGAR returned no record for this ticker"]


def test_extract_annual_revenue_deduplicates(abbv_raw: dict) -> None:
    """AbbVie's XBRL repeats prior-year values across filings. Dedup enforced."""
    facts = abbv_raw["companyfacts"]
    rows = _extract_annual_revenue(facts)

    # Same (year, val) should appear at most once.
    keys = [(r["end"], r["usd"]) for r in rows]
    assert len(keys) == len(set(keys)), "duplicate (end,val) tuples leaked through dedup"


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_sec_smoke() -> None:
    """Live SEC call. Skipped by default."""
    ing = SECEdgarIngester()
    normalized = await ing.ingest("ABBV")
    assert normalized["company"]["sec_cik"] == "1551152"
