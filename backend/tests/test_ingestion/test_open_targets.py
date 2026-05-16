"""Open Targets ingester tests.

Two levels:
  1. Unit tests (fixture-based, no network) — run in CI.
  2. Live integration (`-m live`) — one real call to the Open Targets API.

Fixture is the cached raw payload from `scripts/ingest_adalimumab.py` run;
regenerate when the schema changes.
"""

import json
from pathlib import Path

import pytest

from app.ingestion.open_targets import OpenTargetsIngester


FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "open_targets_CHEMBL1201580.json"


@pytest.fixture
def adalimumab_raw() -> dict:
    """Load cached Open Targets raw payload for adalimumab.

    Fixture is committed under tests/fixtures/ so CI runs offline.
    Refresh by running `scripts/ingest_adalimumab.py` then copying from
    data/raw/open_targets/CHEMBL1201580.json → tests/fixtures/.
    """
    assert FIXTURE_PATH.exists(), (
        f"Missing committed fixture {FIXTURE_PATH} — refresh per docstring."
    )
    return json.loads(FIXTURE_PATH.read_text())


def test_normalize_adalimumab(adalimumab_raw: dict) -> None:
    """The normalize step produces a Phase-0-complete payload for adalimumab."""
    ing = OpenTargetsIngester()
    normalized = ing.normalize(adalimumab_raw)

    drug = normalized["drug"]
    assert drug["chembl_id"] == "CHEMBL1201580"
    assert drug["generic_name"] == "adalimumab"
    assert drug["modality"] == "antibody"
    assert drug["status"] == "approved"
    assert drug["max_phase"] in ("approved", "phase_4")
    assert "TNF" in (drug["mechanism_of_action"] or "")

    targets = normalized["targets"]
    assert any(t["gene_symbol"] == "TNF" for t in targets), (
        f"No TNF target in: {[t['gene_symbol'] for t in targets]}"
    )

    indications = normalized["indications"]
    assert len(indications) >= 5, f"expected ≥5 indications, got {len(indications)}"


def test_validate_rejects_empty() -> None:
    """validate() flags an empty/null drug payload."""
    ing = OpenTargetsIngester()
    errors = ing.validate({})
    assert errors, "validate() must flag empty payload"


def test_validate_rejects_missing_generic_name(adalimumab_raw: dict) -> None:
    """validate() flags missing generic_name."""
    ing = OpenTargetsIngester()
    normalized = ing.normalize(adalimumab_raw)
    normalized["drug"]["generic_name"] = ""
    errors = ing.validate(normalized)
    assert any("generic_name" in e for e in errors)


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_open_targets_smoke() -> None:
    """Live call against Open Targets. Skipped by default (use -m live to run)."""
    ing = OpenTargetsIngester()
    raw = await ing.fetch_raw("CHEMBL1201580")
    assert raw.get("data", {}).get("drug") is not None
