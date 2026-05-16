"""USPTO PatentsView ingester skeleton pending API key.

PatentsView API access requires a registered API key via the `X-Api-Key`
header. Registration: https://patentsview.org/api-key-request

Until PATENTSVIEW_API_KEY is set, fetch_raw raises NotImplementedError
with an actionable message. Curated patents can still flow through
data/curated/drug_patents.yml via apply_curated_patents.
Implementation checklist:
  1. Add PATENTSVIEW_API_KEY to .env
  2. Implement fetch_raw (docs: https://search.patentsview.org/docs/)
  3. normalize extracts patent_id / patent_date / patent_title / assignees / inventors
  4. Sets source_register = PatentSourceRegister.USPTO_MANUAL or a new
     value if we distinguish API-sourced from manual.
"""

from typing import Any

from app.config import settings
from app.ingestion.base import BaseIngester


class USPTOIngester(BaseIngester):
    """Stub ingester — requires PATENTSVIEW_API_KEY."""

    source_name = "uspto_patentsview"

    async def fetch_raw(self, identifier: str) -> dict[str, Any]:
        api_key = getattr(settings, "patentsview_api_key", "") or ""
        if not api_key:
            raise NotImplementedError(
                "USPTOIngester requires a PatentsView API key. Register at "
                "https://patentsview.org/api-key-request, set PATENTSVIEW_API_KEY "
                "in .env, and implement fetch_raw per docs at "
                "https://search.patentsview.org/docs/. Until then, patents flow "
                "through data/curated/drug_patents.yml."
            )
        raise NotImplementedError(
            "fetch_raw implementation pending — see module docstring."
        )

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError("normalize implementation pending.")

    def validate(self, normalized: dict[str, Any]) -> list[str]:
        return ["USPTOIngester not implemented"]


class PurpleBookIngester(BaseIngester):
    """Stub — Purple Book tracks biologic licensure + exclusivity, NOT patents.

    Purple Book download at purplebooksearch.fda.gov exposes CSV/Excel with
    columns like applicant, proper name, dosage form, reference product
    exclusivity end, interchangeability exclusivity end, etc. — no patent
    numbers.

    Biologic patents are accessed via USPTO (PatentsView or bulk). A future
    Purple Book ingest can populate
    reference_product_exclusivity_end on Patent rows created via other
    paths, but doesn't originate patent rows.
    """

    source_name = "purple_book"

    async def fetch_raw(self, identifier: str) -> dict[str, Any]:
        raise NotImplementedError(
            "PurpleBookIngester requires a dedicated parser. Purple Book is a "
            "downloadable Excel, not a REST API; parse with pandas when "
            "biologic exclusivity dates become needed. No patents exposed here."
        )

    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError

    def validate(self, normalized: dict[str, Any]) -> list[str]:
        return ["PurpleBookIngester not implemented"]
