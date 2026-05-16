"""ClinicalTrials.gov v2 ingester (design doc §6.2.3).

Query by intervention name (usually the drug's generic name), fetch all
pages via nextPageToken, return a normalized list of ClinicalTrial
payloads + leadSponsor Company payloads.

Transport note:
  The CT.gov edge uses Cloudflare bot-detection that blocks Python's
  stdlib TLS fingerprint (httpx, requests, aiohttp all return 403).
  We use curl_cffi with Chrome impersonation — drop-in async client
  that passes JA3 checks. This is a compile-time ingester (ADR-0009),
  so the fingerprint workaround lives in the ingestion layer only.
"""

import asyncio
from datetime import date
from typing import Any

from curl_cffi.requests import AsyncSession

from app.config import settings
from app.ingestion.base import BaseIngester


# Paginate in pages of 100. CT.gov caps pageSize; 100 is a comfortable
# batch. Humira has ~784 trials; all pages fetched on full ingest.
PAGE_SIZE = 100

# Per run cap. Humira test requires ≥30; 300 is more than enough for the
# regression case and keeps runtime bounded. Flip to `None` for full pull.
MAX_TRIALS_DEFAULT = 300


def _parse_partial_date(struct: dict[str, Any] | None) -> date | None:
    """CT.gov date shapes: {'date': 'YYYY-MM-DD'} or {'date': 'YYYY-MM'} or {'date': 'YYYY'}."""
    if not struct:
        return None
    raw = struct.get("date")
    if not raw:
        return None
    parts = raw.split("-")
    try:
        year = int(parts[0])
        month = int(parts[1]) if len(parts) > 1 else 1
        day = int(parts[2]) if len(parts) > 2 else 1
        return date(year, month, day)
    except (ValueError, IndexError):
        return None


def _map_phase(phases: list[str] | None) -> str | None:
    """CT.gov phases list (e.g., ['PHASE3']) → BioGraph phase slug."""
    if not phases:
        return None
    # Take the highest phase when trial spans multiple
    ranks = {
        "EARLY_PHASE1": 0, "PHASE1": 1, "PHASE1_PHASE2": 2,
        "PHASE2": 2, "PHASE2_PHASE3": 3, "PHASE3": 3, "PHASE4": 4,
        "NA": -1,
    }
    best = max(phases, key=lambda p: ranks.get(p, -1))
    mapping = {
        "EARLY_PHASE1": "preclinical",
        "PHASE1": "phase_1",
        "PHASE1_PHASE2": "phase_2",
        "PHASE2": "phase_2",
        "PHASE2_PHASE3": "phase_3",
        "PHASE3": "phase_3",
        "PHASE4": "phase_4",
        "NA": None,
    }
    return mapping.get(best)


def _map_status(status: str | None) -> str | None:
    """CT.gov overallStatus → BioGraph TrialStatus slug."""
    if not status:
        return None
    return status.lower()


class ClinicalTrialsIngester(BaseIngester):
    """Ingest all trials for a drug from ClinicalTrials.gov v2 API."""

    source_name = "clinicaltrials"

    def __init__(self, session: AsyncSession | None = None) -> None:
        self._session = session

    async def fetch_raw(self, identifier: str) -> dict[str, Any]:
        """Fetch all pages for a drug's trials.

        `identifier` is the drug's intervention name (e.g., "adalimumab").
        Returns a dict: {studies: list, total_fetched: int, total_count: int|None}.
        """
        owns_session = self._session is None
        session = self._session or AsyncSession(impersonate="chrome")
        try:
            all_studies: list[dict] = []
            next_page_token: str | None = None
            total_count: int | None = None

            while True:
                params: dict[str, Any] = {
                    "query.intr": identifier,
                    "pageSize": PAGE_SIZE,
                    "countTotal": "true",
                }
                if next_page_token:
                    params["pageToken"] = next_page_token

                response = await session.get(settings.clinical_trials_url + "/studies", params=params)
                response.raise_for_status()
                body = response.json()
                if total_count is None:
                    total_count = body.get("totalCount")

                studies = body.get("studies", [])
                all_studies.extend(studies)

                next_page_token = body.get("nextPageToken")
                if not next_page_token or len(all_studies) >= MAX_TRIALS_DEFAULT:
                    break

                # Be polite: CT.gov throttles at ~100 req/min.
                await asyncio.sleep(0.1)

            return {
                "studies": all_studies,
                "total_fetched": len(all_studies),
                "total_count": total_count,
                "query_intervention": identifier,
            }
        finally:
            if owns_session:
                await session.close()

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Flatten each study's protocolSection into our ClinicalTrial shape."""
        trials: list[dict[str, Any]] = []
        companies_by_name: dict[str, dict[str, Any]] = {}

        for study in raw.get("studies", []):
            ps = study.get("protocolSection") or {}
            idm = ps.get("identificationModule") or {}
            sm = ps.get("statusModule") or {}
            dm = ps.get("designModule") or {}
            aim = ps.get("armsInterventionsModule") or {}
            cm = ps.get("conditionsModule") or {}
            om = ps.get("outcomesModule") or {}
            spon = (ps.get("sponsorCollaboratorsModule") or {}).get("leadSponsor") or {}

            nct_id = idm.get("nctId")
            if not nct_id:
                continue

            sponsor_name = (spon.get("name") or "").strip() or None
            if sponsor_name:
                # Normalize Abbott/Abbott Laboratories vs AbbVie later via merge; for now
                # each distinct string is its own company. Phase 1+ adds alias resolution.
                companies_by_name.setdefault(
                    sponsor_name.lower(),
                    {"name": sponsor_name, "sponsor_class": spon.get("class")},
                )

            trials.append(
                {
                    "nct_id": nct_id,
                    "title": idm.get("officialTitle") or idm.get("briefTitle"),
                    "phase": _map_phase(dm.get("phases")),
                    "status": _map_status(sm.get("overallStatus")),
                    "enrollment": (dm.get("enrollmentInfo") or {}).get("count"),
                    "start_date": _parse_partial_date(sm.get("startDateStruct")),
                    "completion_date": _parse_partial_date(sm.get("completionDateStruct")),
                    "conditions": cm.get("conditions") or [],
                    "primary_outcomes": om.get("primaryOutcomes") or [],
                    "secondary_outcomes": om.get("secondaryOutcomes") or [],
                    "interventions": aim.get("interventions") or [],
                    "sponsor_name": sponsor_name,
                }
            )

        return {
            "trials": trials,
            "companies": list(companies_by_name.values()),
            "_query_intervention": raw.get("query_intervention"),
            "_total_fetched": raw.get("total_fetched"),
            "_total_available": raw.get("total_count"),
        }

    def validate(self, normalized: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if "trials" not in normalized:
            errors.append("normalized payload missing 'trials' key")
        for t in normalized.get("trials", []):
            if not t.get("nct_id"):
                errors.append(f"trial missing nct_id: {t}")
        return errors
