"""Open Targets GraphQL ingester (design doc §6.2.1).

Primary responsibility: map a ChEMBL drug ID → structured Drug payload
including linked targets and indications.

Schema notes (verified against live API 2026-04):
  - `maximumClinicalStage` (not `maximumClinicalTrialPhase` as in design doc v1.0);
    returns values like "APPROVAL", "PHASE_4", "PHASE_3", "PRECLINICAL".
  - `ClinicalIndicationFromDrug.maxClinicalStage` (not `maxPhaseForIndication`).
  - No `linkedTargets` field on Drug — derive targets from mechanismsOfAction.rows.
  - No `yearOfFirstApproval` / `hasBeenWithdrawn` on current v4 schema.

Design doc v1.2 should be patched when this ingester stabilizes.
"""

from typing import Any

import httpx

from app.config import settings
from app.ingestion.base import BaseIngester


DRUG_QUERY = """
query DrugInfo($chemblId: String!) {
  drug(chemblId: $chemblId) {
    id
    name
    synonyms
    tradeNames
    drugType
    maximumClinicalStage
    mechanismsOfAction {
      rows {
        mechanismOfAction
        actionType
        targets {
          id
          approvedSymbol
          approvedName
        }
      }
    }
    indications {
      rows {
        maxClinicalStage
        disease {
          id
          name
        }
      }
    }
  }
}
"""


def _map_drug_type(drug_type: str | None) -> str | None:
    """Open Targets drugType (e.g., 'Antibody') → BioGraph modality slug."""
    if not drug_type:
        return None
    return drug_type.lower().replace(" ", "_")


def _map_stage(stage: str | None) -> str | None:
    """Open Targets stage ('APPROVAL', 'PHASE_4', ...) → BioGraph phase slug."""
    if not stage:
        return None
    mapping = {
        "APPROVAL": "approved",
        "APPROVED": "approved",
        "PHASE_4": "phase_4",
        "PHASE_3": "phase_3",
        "PHASE_2": "phase_2",
        "PHASE_1": "phase_1",
        "PRECLINICAL": "preclinical",
    }
    return mapping.get(stage.upper(), stage.lower())


def _status_from_stage(stage: str | None) -> str:
    """Coarse status derived from max stage."""
    if not stage:
        return "investigational"
    s = stage.upper()
    if s in ("APPROVAL", "APPROVED", "PHASE_4"):
        return "approved"
    return "investigational"


class OpenTargetsIngester(BaseIngester):
    """Ingest a single drug by its ChEMBL ID from Open Targets Platform."""

    source_name = "open_targets"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_raw(self, identifier: str) -> dict[str, Any]:
        """Fetch the Drug GraphQL payload for a ChEMBL ID."""
        client = self._client or httpx.AsyncClient(timeout=30.0)
        owns_client = self._client is None
        try:
            response = await client.post(
                settings.open_targets_url,
                json={"query": DRUG_QUERY, "variables": {"chemblId": identifier}},
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
        finally:
            if owns_client:
                await client.aclose()

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Shape the GraphQL response into BioGraph Drug+Target+Indication dicts."""
        if raw.get("errors"):
            return {"_errors": raw["errors"]}
        if raw.get("data") is None or raw["data"].get("drug") is None:
            return {}

        d = raw["data"]["drug"]

        # Mechanisms → mechanism_of_action text + target list
        moa_rows = (d.get("mechanismsOfAction") or {}).get("rows", []) or []
        moa_strings = [r["mechanismOfAction"] for r in moa_rows if r.get("mechanismOfAction")]
        mechanism_of_action = "; ".join(sorted(set(moa_strings))) or None

        # Targets come only from mechanismsOfAction in current v4 schema
        seen_target_ids: set[str] = set()
        targets: list[dict[str, Any]] = []
        for row in moa_rows:
            for t in row.get("targets") or []:
                if t["id"] in seen_target_ids:
                    continue
                seen_target_ids.add(t["id"])
                targets.append(
                    {
                        "ensembl_id": t["id"],
                        "gene_symbol": t.get("approvedSymbol"),
                        "approved_name": t.get("approvedName"),
                    }
                )

        # Indications
        indication_rows = (d.get("indications") or {}).get("rows", []) or []
        indications: list[dict[str, Any]] = []
        seen_efo: set[str] = set()
        for r in indication_rows:
            disease = r.get("disease") or {}
            efo_id = disease.get("id")
            if not efo_id or efo_id in seen_efo:
                continue
            seen_efo.add(efo_id)
            indications.append(
                {
                    "efo_id": efo_id,
                    "name": disease.get("name"),
                    "max_phase": _map_stage(r.get("maxClinicalStage")),
                }
            )

        max_stage = d.get("maximumClinicalStage")

        return {
            "drug": {
                "chembl_id": d["id"],
                "generic_name": (d.get("name") or "").lower(),
                "aliases": d.get("synonyms") or [],
                "brand_names": d.get("tradeNames") or [],
                "modality": _map_drug_type(d.get("drugType")),
                "max_phase": _map_stage(max_stage),
                "status": _status_from_stage(max_stage),
                "mechanism_of_action": mechanism_of_action,
            },
            "targets": targets,
            "indications": indications,
            "_source": "open_targets",
            "_raw_drug_id": d["id"],
        }

    def validate(self, normalized: dict[str, Any]) -> list[str]:
        """Minimum data-integrity checks."""
        errors: list[str] = []
        if "_errors" in normalized:
            errors.append(f"GraphQL errors: {normalized['_errors']}")
            return errors
        if not normalized:
            return ["Open Targets returned no drug record (null data.drug)"]
        drug = normalized.get("drug") or {}
        if not drug.get("chembl_id"):
            errors.append("drug.chembl_id missing")
        if not drug.get("generic_name"):
            errors.append("drug.generic_name missing")
        return errors
