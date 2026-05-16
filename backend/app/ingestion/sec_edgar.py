"""SEC EDGAR ingester — Company metadata (CIK, ticker, name).

Scope (Phase 1 Day 3): Company-level identifiers only. XBRL companyfacts
exposes `us-gaap:Revenues` at the Company level but NOT product-level
(no clean `abbv:HumiraNetRevenues` tag). Product-level numbers are
curated separately in data/curated/drug_financials.yml.

Transport: plain httpx with mandatory User-Agent per SEC policy.
"""

from typing import Any

import httpx

from app.config import settings
from app.ingestion.base import BaseIngester


TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
COMPANYFACTS_URL = "https://data.sec.gov/api/xbrl/companyfacts/CIK{cik:010d}.json"


async def resolve_ticker_to_cik(ticker: str, client: httpx.AsyncClient) -> dict[str, Any] | None:
    """Look up a company by ticker in SEC's company_tickers.json."""
    r = await client.get(TICKERS_URL)
    r.raise_for_status()
    tickers = r.json()
    target = ticker.upper()
    for _, entry in tickers.items():
        if entry.get("ticker") == target:
            return {
                "cik": int(entry["cik_str"]),
                "ticker": target,
                "name": entry.get("title"),
            }
    return None


def _extract_annual_revenue(facts: dict[str, Any]) -> list[dict[str, Any]]:
    """Dedup FY Revenues entries; return sorted [{year, usd}] list."""
    usgaap = (facts.get("facts") or {}).get("us-gaap") or {}
    rev = usgaap.get("Revenues")
    if not rev:
        return []
    usd_rows = (rev.get("units") or {}).get("USD") or []
    # Full-year 10-K entries only; dedup on (end, val) — SEC repeats
    # prior-year restatements across filings.
    seen: set[tuple[str, int]] = set()
    rows: list[dict[str, Any]] = []
    for r in usd_rows:
        if r.get("fp") != "FY" or r.get("form") != "10-K":
            continue
        key = (r["end"], r["val"])
        if key in seen:
            continue
        seen.add(key)
        rows.append({"year": int(r["end"][:4]), "usd": int(r["val"]), "end": r["end"]})
    rows.sort(key=lambda x: x["end"])
    return rows


class SECEdgarIngester(BaseIngester):
    """Ingest Company-level identifiers + revenue history from SEC EDGAR."""

    source_name = "sec_edgar"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_raw(self, identifier: str) -> dict[str, Any]:
        """`identifier` is a stock ticker (e.g., 'ABBV'). Returns
        {ticker_entry, companyfacts}."""
        headers = {
            "User-Agent": settings.sec_user_agent,
            "Accept": "application/json",
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0, headers=headers)
        try:
            # If client was passed in, use its headers; otherwise apply ours above
            if not owns_client:
                client.headers.update(headers)

            ticker_entry = await resolve_ticker_to_cik(identifier, client)
            if ticker_entry is None:
                return {"ticker_entry": None, "companyfacts": None, "_identifier": identifier}

            cik = ticker_entry["cik"]
            r = await client.get(COMPANYFACTS_URL.format(cik=cik))
            r.raise_for_status()
            return {
                "ticker_entry": ticker_entry,
                "companyfacts": r.json(),
                "_identifier": identifier,
            }
        finally:
            if owns_client:
                await client.aclose()

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        entry = raw.get("ticker_entry")
        if not entry:
            return {}
        facts = raw.get("companyfacts") or {}
        revenues = _extract_annual_revenue(facts)
        return {
            "company": {
                "sec_cik": str(entry["cik"]),
                "ticker": entry["ticker"],
                "name": entry.get("name") or facts.get("entityName"),
            },
            "annual_revenues": revenues,
            "_source": "sec_edgar",
        }

    def validate(self, normalized: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if not normalized:
            return ["SEC EDGAR returned no record for this ticker"]
        company = normalized.get("company") or {}
        if not company.get("sec_cik"):
            errors.append("company.sec_cik missing")
        if not company.get("ticker"):
            errors.append("company.ticker missing")
        if not company.get("name"):
            errors.append("company.name missing")
        return errors
