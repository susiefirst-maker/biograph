"""openFDA Drugs@FDA ingester unit tests (fixture-based, no network)."""

import json
from datetime import date
from pathlib import Path

import pytest

from app.ingestion.fda import (
    FDAIngester,
    _map_action_type,
    _parse_yyyymmdd,
    _split_application_number,
)


FIXTURE_PATH = Path(__file__).parent.parent / "fixtures" / "fda_adalimumab.json"


@pytest.fixture
def adalimumab_fda_raw() -> dict:
    assert FIXTURE_PATH.exists()
    return json.loads(FIXTURE_PATH.read_text())


def test_normalize_adalimumab_fda(adalimumab_fda_raw: dict) -> None:
    ing = FDAIngester()
    raw = {**adalimumab_fda_raw, "_query_generic": "adalimumab"}
    normalized = ing.normalize(raw)

    decisions = normalized["decisions"]
    companies = normalized["companies"]

    assert len(decisions) > 100, f"expected >100 approved decisions, got {len(decisions)}"
    assert len(companies) >= 3, "expected ≥3 distinct sponsor companies"

    for d in decisions:
        assert d["application_number"].startswith(("BLA", "NDA"))
        assert d["jurisdiction"] == "FDA"
        assert d["submission_number"], "submission_number missing"

    # AbbVie's Humira originator application is BLA125057 — find it
    humira_decisions = [d for d in decisions if d["application_number"] == "BLA125057"]
    assert humira_decisions, "Humira's BLA125057 not found in normalized output"
    assert all(d["_is_originator"] for d in humira_decisions), (
        "BLA125057 submissions should be flagged originator"
    )

    # At least one biosimilar (ADALIMUMAB-<suffix>) present AND marked non-originator
    biosimilar_decisions = [
        d for d in decisions
        if any("-" in g for g in d["_generic_names"])
    ]
    assert biosimilar_decisions, "expected biosimilar decisions in mixed fixture"
    assert not any(d["_is_originator"] for d in biosimilar_decisions)


def test_validate_flags_missing_application_number() -> None:
    ing = FDAIngester()
    errors = ing.validate({"decisions": [{"application_number": None, "jurisdiction": "FDA"}]})
    assert any("application_number" in e for e in errors)


def test_validate_flags_wrong_jurisdiction() -> None:
    ing = FDAIngester()
    errors = ing.validate({"decisions": [{"application_number": "BLA1", "jurisdiction": "EMA"}]})
    assert any("jurisdiction" in e for e in errors)


@pytest.mark.parametrize(
    "app_num, expected",
    [
        ("BLA125057", ("125057", None)),
        ("NDA021345", (None, "021345")),
        ("ANDA090123", (None, None)),  # ANDA isn't handled in Phase 1
        ("", (None, None)),
    ],
)
def test_split_application_number(app_num, expected) -> None:
    assert _split_application_number(app_num) == expected


@pytest.mark.parametrize(
    "sub_type, class_code, expected",
    [
        ("ORIG", None, "approval"),
        ("SUPPL", "LABELING", "label_change"),
        ("SUPPL", "EFFICACY", "efficacy_supplement"),
        ("SUPPL", "MANUFACTURING", "manufacturing_change"),
        ("SUPPL", "OTHER", "supplement"),
        (None, None, "other"),
    ],
)
def test_map_action_type(sub_type, class_code, expected) -> None:
    assert _map_action_type(sub_type, class_code) == expected


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("20240430", date(2024, 4, 30)),
        ("20021231", date(2002, 12, 31)),
        ("", None),
        (None, None),
        ("2024", None),  # wrong length
        ("20240230", None),  # bad date (Feb 30)
    ],
)
def test_parse_yyyymmdd(raw, expected) -> None:
    assert _parse_yyyymmdd(raw) == expected


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_fda_smoke() -> None:
    """Live openFDA call. Skipped by default."""
    ing = FDAIngester()
    normalized = await ing.ingest("adalimumab")
    assert normalized["_total_records"] >= 5
