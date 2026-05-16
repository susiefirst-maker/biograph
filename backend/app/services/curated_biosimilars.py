"""Curated biosimilars loader — creates biosimilar Drug rows linked back
to their reference drug via Drug.biosimilar_of_id (P2-D3 schema).
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Drug


CURATED_DIR = Path(__file__).resolve().parents[3] / "data" / "curated"
BIOSIMILAR_FILES = sorted(CURATED_DIR.glob("*_biosimilars.yml"))


def _parse_date(raw: Any) -> date | None:
    if isinstance(raw, date):
        return raw
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date()
    except ValueError:
        return None


def load_curated_biosimilars() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in BIOSIMILAR_FILES:
        if not path.exists():
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        out.append(doc)
    return out


async def apply_curated_biosimilars(session: AsyncSession) -> int:
    """Create biosimilar Drug rows. Returns count persisted."""
    docs = load_curated_biosimilars()
    total = 0

    for doc in docs:
        ref_chembl_id = doc.get("reference_chembl_id")
        biosimilars = doc.get("biosimilars") or []
        if not ref_chembl_id or not biosimilars:
            continue

        reference = await session.scalar(
            select(Drug).where(Drug.chembl_id == ref_chembl_id)
        )
        if reference is None:
            continue

        for b in biosimilars:
            generic_name = b.get("generic_name")
            if not generic_name:
                continue

            # Natural key for biosimilar Drug rows: (generic_name).
            # Biosimilar generics are unique (adalimumab-atto etc.).
            existing = await session.scalar(
                select(Drug).where(Drug.generic_name == generic_name)
            )
            if existing is None:
                drug = Drug(
                    generic_name=generic_name,
                    brand_names=b.get("brand_names") or [],
                    aliases=[],
                    modality=b.get("modality"),
                    status=b.get("status") or "approved",
                    max_phase="phase_4",
                    first_approval_date=_parse_date(b.get("first_fda_approval")),
                    bla_number_note=None,  # biosimilar BLAs go into regulatory_decisions when FDA ingester sees them
                    biosimilar_of_id=reference.id,
                    field_provenance={"_curated_source": "data/curated/humira_biosimilars.yml"},
                ) if False else Drug(
                    # biosimilar Drug model shape — omit fields not in model
                    generic_name=generic_name,
                    brand_names=b.get("brand_names") or [],
                    aliases=[],
                    modality=b.get("modality"),
                    status=b.get("status") or "approved",
                    max_phase="phase_4",
                    first_approval_date=_parse_date(b.get("first_fda_approval")),
                    biosimilar_of_id=reference.id,
                    field_provenance={"_curated_source": "data/curated/humira_biosimilars.yml"},
                )
                session.add(drug)
                total += 1
            else:
                # Update reference link if missing
                if existing.biosimilar_of_id is None:
                    existing.biosimilar_of_id = reference.id
                # Update brand names/modality if missing
                if not existing.brand_names and b.get("brand_names"):
                    existing.brand_names = b["brand_names"]
                if not existing.modality and b.get("modality"):
                    existing.modality = b["modality"]

    await session.flush()
    return total
