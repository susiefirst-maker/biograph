"""Curated drug-patents loader — verifies YAML shape + Humira anchor."""

from app.services.curated_patents import DRUG_PATENTS_FILE, load_drug_patents


def test_drug_patents_file_exists() -> None:
    assert DRUG_PATENTS_FILE.exists(), f"expected {DRUG_PATENTS_FILE}"


def test_humira_core_patent_curated() -> None:
    entries = load_drug_patents()
    humira = next((e for e in entries if e.get("chembl_id") == "CHEMBL1201580"), None)
    assert humira is not None, "Humira (CHEMBL1201580) must be curated in drug_patents.yml"

    patents = humira.get("patents") or []
    core = next((p for p in patents if p.get("patent_number") == "6090382"), None)
    assert core is not None, "Humira core patent US6090382 must be present"
    assert core.get("source_register") == "uspto_manual"
    assert core.get("citations"), "every curated patent must cite source"
    assert core.get("expiry_date")


def test_backfill_note_present() -> None:
    """Until PatentsView key or I-MAK list arrives, the YAML must document the gap."""
    entries = load_drug_patents()
    humira = next((e for e in entries if e.get("chembl_id") == "CHEMBL1201580"), None)
    assert humira and humira.get("patent_backfill_note"), (
        "drug_patents.yml Humira entry must carry patent_backfill_note "
        "until Phase 1 Day 5 lands the thicket backfill"
    )
