"""Full per-drug ingest orchestrator.

Runs the 6-step Phase-0 + Phase-1 pipeline on a single drug:
  1. Open Targets (drug + targets + indications)
  2. ClinicalTrials.gov (trials + sponsor companies)
  3. openFDA Drugs@FDA (regulatory decisions)
  4. SEC EDGAR (Company entities for originator tickers)
  5. Curated financials (data/curated/drug_financials.yml)
  6. Curated patents (data/curated/drug_patents.yml)

Per-drug scripts (scripts/ingest_adalimumab.py etc.) are thin wrappers
that supply a DrugIngestSpec. Batch ingest (Phase 1 Day 6+) will iterate
over a list of specs.
"""

from dataclasses import dataclass, field
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db import get_session
from app.ingestion.clinicaltrials import ClinicalTrialsIngester
from app.ingestion.fda import FDAIngester
from app.ingestion.open_targets import OpenTargetsIngester
from app.ingestion.sec_edgar import SECEdgarIngester
from app.models import Drug
from app.services.clinical_trial_service import upsert_clinical_trials_from_ctgov
from app.services.curated_financials import apply_curated_financials
from app.services.curated_patents import apply_curated_patents
from app.services.drug_service import upsert_drug_from_open_targets
from app.services.regulatory_decision_service import (
    upsert_regulatory_decisions_from_fda,
)
from app.services.sec_service import upsert_company_from_sec


@dataclass
class DrugIngestSpec:
    """Inputs for a single-drug ingest run."""

    chembl_id: str
    generic_name: str
    originator_tickers: list[str] = field(default_factory=list)

    # Optional: set drug.originator_id after ingest to the first Company
    # whose CIK corresponds to the first originator_ticker resolved.
    link_originator: bool = True


@dataclass
class DrugIngestReport:
    """What the pipeline actually ingested."""

    drug_id: UUID
    chembl_id: str
    generic_name: str
    target_count: int
    indication_count: int
    trials_count: int
    regulatory_decisions_linked: int
    regulatory_decisions_total: int
    ct_total_available: int | None
    companies_resolved_from_sec: list[dict]
    curated_financials_applied: int
    curated_patents_applied: int


async def ingest_drug_full(spec: DrugIngestSpec) -> DrugIngestReport:
    """Run the 6-step pipeline end-to-end. Returns a report for the caller to render/assert."""
    # 1. Open Targets
    ot = OpenTargetsIngester()
    ot_normalized = await ot.ingest(spec.chembl_id)

    async with get_session() as session:
        drug = await upsert_drug_from_open_targets(session, ot_normalized)
        drug_id = drug.id

    # 2. ClinicalTrials.gov
    ct = ClinicalTrialsIngester()
    ct_normalized = await ct.ingest(spec.generic_name)
    async with get_session() as session:
        persisted_trials = await upsert_clinical_trials_from_ctgov(
            session, drug_id, ct_normalized
        )

    # 3. openFDA Drugs@FDA
    fda = FDAIngester()
    fda_normalized = await fda.ingest(spec.generic_name)
    async with get_session() as session:
        persisted_decisions = await upsert_regulatory_decisions_from_fda(
            session, drug_id, fda_normalized
        )
        linked = sum(1 for d in persisted_decisions if d.drug_id == drug_id)

    # 4. SEC EDGAR for each originator ticker
    sec = SECEdgarIngester()
    companies_resolved: list[dict] = []
    originator_company_id: UUID | None = None
    for i, ticker in enumerate(spec.originator_tickers):
        try:
            sec_normalized = await sec.ingest(ticker)
        except Exception as exc:
            companies_resolved.append({"ticker": ticker, "error": f"{type(exc).__name__}: {exc}"})
            continue
        async with get_session() as session:
            company = await upsert_company_from_sec(session, sec_normalized)
            if company is None:
                continue
            companies_resolved.append(
                {
                    "ticker": ticker,
                    "name": company.name,
                    "cik": company.sec_cik,
                    "revenue_years": len(sec_normalized.get("annual_revenues", []) or []),
                }
            )
            if i == 0 and spec.link_originator:
                originator_company_id = company.id

    # Link drug.originator_id if first ticker resolved
    if originator_company_id and spec.link_originator:
        async with get_session() as session:
            drug_row = await session.scalar(select(Drug).where(Drug.id == drug_id))
            if drug_row and drug_row.originator_id is None:
                drug_row.originator_id = originator_company_id

    # 5. Curated financials
    async with get_session() as session:
        fin_n = await apply_curated_financials(session)

    # 6. Curated patents
    async with get_session() as session:
        pat_n = await apply_curated_patents(session)

    return DrugIngestReport(
        drug_id=drug_id,
        chembl_id=spec.chembl_id,
        generic_name=spec.generic_name,
        target_count=len(ot_normalized.get("targets", [])),
        indication_count=len(ot_normalized.get("indications", [])),
        trials_count=len(persisted_trials),
        regulatory_decisions_linked=linked,
        regulatory_decisions_total=len(persisted_decisions),
        ct_total_available=ct_normalized.get("_total_available"),
        companies_resolved_from_sec=companies_resolved,
        curated_financials_applied=fin_n,
        curated_patents_applied=pat_n,
    )


async def fetch_drug_summary(chembl_id: str) -> dict:
    """Re-read the persisted drug with all Day 4-era relationships eager-loaded."""
    async with get_session() as session:
        drug = await session.scalar(
            select(Drug)
            .where(Drug.chembl_id == chembl_id)
            .options(
                selectinload(Drug.targets),
                selectinload(Drug.indications),
                selectinload(Drug.trials),
                selectinload(Drug.regulatory_decisions),
                selectinload(Drug.patents),
            )
        )
        if drug is None:
            return {}
        return {
            "id": drug.id,
            "generic_name": drug.generic_name,
            "chembl_id": drug.chembl_id,
            "modality": drug.modality,
            "max_phase": drug.max_phase,
            "status": drug.status,
            "mechanism_of_action": drug.mechanism_of_action,
            "brand_names": list(drug.brand_names or []),
            "originator_id": drug.originator_id,
            "revenue_peak_usd": drug.revenue_peak_usd,
            "revenue_peak_year": drug.revenue_peak_year,
            "targets": [(t.gene_symbol, t.ensembl_id) for t in drug.targets],
            "indications": [i.name for i in drug.indications],
            "trials": [t.nct_id for t in drug.trials],
            "regulatory_decisions": [
                (d.application_number, d.action_type, str(d.decision_date))
                for d in drug.regulatory_decisions
            ],
            "patents": [(p.patent_number, str(p.expiry_date)) for p in drug.patents],
        }
