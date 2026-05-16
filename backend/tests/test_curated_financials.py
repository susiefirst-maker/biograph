"""Curated drug-financials loader — verifies YAML shape + Humira values."""

from app.services.curated_financials import DRUG_FINANCIALS_FILE, load_drug_financials


def test_drug_financials_file_exists() -> None:
    assert DRUG_FINANCIALS_FILE.exists(), f"expected {DRUG_FINANCIALS_FILE}"


def test_humira_peak_curated() -> None:
    entries = load_drug_financials()
    humira = next((e for e in entries if e.get("chembl_id") == "CHEMBL1201580"), None)
    assert humira is not None, "Humira (CHEMBL1201580) must be curated in drug_financials.yml"
    assert humira["revenue_peak_usd"] >= 20_000_000_000
    assert humira["revenue_peak_year"] == 2021
    assert humira.get("source_refs"), "every curated entry must cite source_refs"
