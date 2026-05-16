"""ClinicalTrials.gov ingester unit tests (fixture-based, no network)."""

import json
from datetime import date
from pathlib import Path

import pytest

from app.ingestion.clinicaltrials import (
    ClinicalTrialsIngester,
    _map_phase,
    _map_status,
    _parse_partial_date,
)


FIXTURE_PATH = (
    Path(__file__).parent.parent / "fixtures" / "clinicaltrials_adalimumab.json"
)


@pytest.fixture
def adalimumab_trials_raw() -> dict:
    assert FIXTURE_PATH.exists()
    return json.loads(FIXTURE_PATH.read_text())


def test_normalize_adalimumab_trials(adalimumab_trials_raw: dict) -> None:
    ing = ClinicalTrialsIngester()
    normalized = ing.normalize(adalimumab_trials_raw)

    trials = normalized["trials"]
    companies = normalized["companies"]

    assert len(trials) == 40, f"expected 40 trials (trimmed fixture), got {len(trials)}"
    assert len(companies) >= 1, "expected ≥1 sponsor company"

    # Every trial has required fields
    for t in trials:
        assert t["nct_id"], "trial missing nct_id"
        assert t["nct_id"].startswith("NCT"), f"invalid nct_id: {t['nct_id']!r}"

    # Spot-check the first trial against known fixture content
    first = trials[0]
    assert first["nct_id"] == "NCT00870467"
    assert "Abbott" in first["sponsor_name"]


def test_validate_flags_missing_nct_id() -> None:
    ing = ClinicalTrialsIngester()
    errors = ing.validate({"trials": [{"nct_id": None, "title": "ghost"}]})
    assert any("nct_id" in e for e in errors)


def test_validate_flags_missing_trials_key() -> None:
    ing = ClinicalTrialsIngester()
    errors = ing.validate({})
    assert any("trials" in e for e in errors)


@pytest.mark.parametrize(
    "phases, expected",
    [
        (["PHASE3"], "phase_3"),
        (["PHASE1", "PHASE2"], "phase_2"),
        (["PHASE4"], "phase_4"),
        (["EARLY_PHASE1"], "preclinical"),
        (["NA"], None),
        ([], None),
        (None, None),
    ],
)
def test_map_phase(phases, expected) -> None:
    assert _map_phase(phases) == expected


@pytest.mark.parametrize(
    "struct, expected",
    [
        ({"date": "2024-03-14"}, date(2024, 3, 14)),
        ({"date": "2024-03"}, date(2024, 3, 1)),
        ({"date": "2024"}, date(2024, 1, 1)),
        ({"date": ""}, None),
        (None, None),
        ({}, None),
    ],
)
def test_parse_partial_date(struct, expected) -> None:
    assert _parse_partial_date(struct) == expected


def test_map_status_lowercases() -> None:
    assert _map_status("COMPLETED") == "completed"
    assert _map_status(None) is None


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_ctgov_smoke() -> None:
    """Live call against CT.gov. Requires curl_cffi (bypasses Cloudflare TLS)."""
    ing = ClinicalTrialsIngester()
    raw = await ing.fetch_raw("adalimumab")
    assert raw["total_fetched"] >= 30
