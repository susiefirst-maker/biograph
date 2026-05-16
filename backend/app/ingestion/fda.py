"""openFDA Drugs@FDA ingester (design doc §6.2.4).

Query: https://api.fda.gov/drug/drugsfda.json?search=openfda.generic_name:"adalimumab"

Each API result is one BLA/NDA application with a `submissions[]` list.
We flatten submissions → one RegulatoryDecision row each.

Transport: plain httpx works (no Cloudflare block).
"""

from datetime import date
from typing import Any

import httpx

from app.config import settings
from app.ingestion.base import BaseIngester


PAGE_SIZE = 100


def _parse_yyyymmdd(s: str | None) -> date | None:
    if not s or len(s) != 8:
        return None
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except (ValueError, TypeError):
        return None


def _split_application_number(app_num: str) -> tuple[str | None, str | None]:
    """"BLA761058" → ("761058", None). "NDA125057" → (None, "125057")."""
    if not app_num:
        return (None, None)
    if app_num.startswith("BLA"):
        return (app_num[3:], None)
    if app_num.startswith("NDA"):
        return (None, app_num[3:])
    return (None, None)


def _map_action_type(submission_type: str | None, class_code: str | None) -> str:
    """Coarse action taxonomy for BioGraph filters."""
    if submission_type == "ORIG":
        return "approval"
    if submission_type == "SUPPL":
        if class_code in ("LABELING", "LAB"):
            return "label_change"
        if class_code == "EFFICACY":
            return "efficacy_supplement"
        if class_code == "MANUFACTURING":
            return "manufacturing_change"
        return "supplement"
    return "other"


class FDAIngester(BaseIngester):
    """Ingest all Drugs@FDA applications for a generic drug name."""

    source_name = "fda"

    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch_raw(self, identifier: str) -> dict[str, Any]:
        """Fetch all applications matching `openfda.generic_name:"<identifier>"`.

        Handles the (small) pagination via skip. Total adalimumab results ~11;
        most drugs have <100 applications, so we cap at one page.

        404 = no matching records (older drugs, non-FDA-approved generics);
        treated as empty result, not an error.
        """
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=30.0)
        try:
            params = {
                "search": f'openfda.generic_name:"{identifier}"',
                "limit": PAGE_SIZE,
            }
            r = await client.get(settings.fda_url + "/drug/drugsfda.json", params=params)
            if r.status_code == 404:
                return {"results": [], "meta": {"results": {"total": 0}}}
            r.raise_for_status()
            return r.json()
        finally:
            if owns_client:
                await client.aclose()

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Flatten each application's submissions → one decision per submission."""
        decisions: list[dict[str, Any]] = []
        companies_by_name: dict[str, dict[str, Any]] = {}

        for app in raw.get("results", []):
            app_num = app.get("application_number", "") or ""
            bla_number, nda_number = _split_application_number(app_num)

            openfda = app.get("openfda") or {}
            generic_names = [g.upper() for g in (openfda.get("generic_name") or [])]
            # Originator when exact match on the searched generic
            # (ADALIMUMAB vs biosimilar ADALIMUMAB-ADBM / -ATTO / etc.)
            is_originator = any(
                g.upper() == (raw.get("_query_generic") or "").upper() for g in generic_names
            ) if raw.get("_query_generic") else False

            sponsor_name = (app.get("sponsor_name") or "").strip() or None
            if sponsor_name:
                companies_by_name.setdefault(
                    sponsor_name.lower(),
                    {"name": sponsor_name, "sponsor_class": "SPONSOR"},
                )

            for sub in app.get("submissions") or []:
                # Only persist approved decisions in v1 (AP = Approved).
                if sub.get("submission_status") != "AP":
                    continue

                sub_num = sub.get("submission_number")
                sub_type = sub.get("submission_type")  # ORIG / SUPPL
                class_code = sub.get("submission_class_code")
                decision_date = _parse_yyyymmdd(sub.get("submission_status_date"))

                docs = [
                    doc.get("url")
                    for doc in (sub.get("application_docs") or [])
                    if doc.get("url")
                ]

                decisions.append(
                    {
                        "application_number": app_num,
                        "bla_number": bla_number,
                        "nda_number": nda_number,
                        "jurisdiction": "FDA",
                        "action_type": _map_action_type(sub_type, class_code),
                        "decision_date": decision_date,
                        "notes": sub.get("submission_class_code_description"),
                        "review_documents": docs,
                        "submission_number": sub_num,
                        "submission_type": sub_type,
                        "review_priority": sub.get("review_priority"),
                        "sponsor_name": sponsor_name,
                        "_is_originator": is_originator,
                        "_generic_names": generic_names,
                    }
                )

        return {
            "decisions": decisions,
            "companies": list(companies_by_name.values()),
            "_total_records": len(raw.get("results", [])),
        }

    def validate(self, normalized: dict[str, Any]) -> list[str]:
        errors: list[str] = []
        if "decisions" not in normalized:
            errors.append("normalized payload missing 'decisions' key")
        for d in normalized.get("decisions", []):
            if not d.get("application_number"):
                errors.append(f"decision missing application_number: {d}")
            if d.get("jurisdiction") != "FDA":
                errors.append(f"decision has wrong jurisdiction: {d.get('jurisdiction')!r}")
        return errors

    async def ingest(self, identifier: str) -> dict[str, Any]:
        """Override to stash the query identifier so normalize can filter originator rows."""
        raw = await self.fetch_raw(identifier)
        self._save_raw(identifier, raw)
        raw["_query_generic"] = identifier
        normalized = self.normalize(raw)
        errors = self.validate(normalized)
        if errors:
            from app.ingestion.base import ValidationError

            raise ValidationError(errors)
        return normalized
