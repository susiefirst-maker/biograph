"""Build the 100-drug batch ingest list from ChEMBL.

Fetches approved drugs (max_phase=4) with preferred names, across a mix
of modalities (small molecule + biologic). Caches the result to
data/curated/batch_drug_list.json so batch ingest runs are reproducible.

Run once:
  PYTHONPATH=. python scripts/build_batch_list.py

The cached file is committed; don't regenerate unless you want to
refresh the drug set.
"""

import asyncio
import json
import sys
from pathlib import Path

import httpx


BATCH_FILE = Path(__file__).resolve().parents[2] / "data" / "curated" / "batch_drug_list.json"
CHEMBL_URL = "https://www.ebi.ac.uk/chembl/api/data/molecule.json"

SMALL_MOL_TARGET = 300
ANTIBODY_TARGET = 120
PROTEIN_TARGET = 80

# ChEMBL paginates with limit ≤1000 but is slow; fetch in batches of 200.
PAGE_SIZE = 200


async def fetch(client: httpx.AsyncClient, molecule_type: str, want: int) -> list[dict]:
    """Page through ChEMBL until we have `want` drugs with preferred names."""
    collected: list[dict] = []
    offset = 0
    while len(collected) < want:
        params = {
            "max_phase": 4,
            "molecule_type": molecule_type,
            "limit": PAGE_SIZE,
            "offset": offset,
            "only": "molecule_chembl_id,pref_name,molecule_type",
        }
        r = await client.get(CHEMBL_URL, params=params)
        r.raise_for_status()
        page = r.json().get("molecules", [])
        if not page:
            break  # no more data
        collected.extend(
            {
                "chembl_id": m["molecule_chembl_id"],
                "generic_name": (m.get("pref_name") or "").lower() or None,
                "modality_source": molecule_type,
            }
            for m in page
            if m.get("pref_name")
        )
        offset += PAGE_SIZE
    return collected[:want]


async def main() -> int:
    async with httpx.AsyncClient(timeout=60.0) as client:
        small_mol = await fetch(client, "Small molecule", SMALL_MOL_TARGET)
        antibodies = await fetch(client, "Antibody", ANTIBODY_TARGET)
        proteins = await fetch(client, "Protein", PROTEIN_TARGET)

    drugs = small_mol + antibodies + proteins

    # Dedup on chembl_id (paranoid — shouldn't collide but can't hurt)
    seen: set[str] = set()
    deduped: list[dict] = []
    for d in drugs:
        if d["chembl_id"] in seen:
            continue
        seen.add(d["chembl_id"])
        deduped.append(d)

    BATCH_FILE.parent.mkdir(parents=True, exist_ok=True)
    BATCH_FILE.write_text(json.dumps({"count": len(deduped), "drugs": deduped}, indent=2))
    print(f"wrote {len(deduped)} drugs to {BATCH_FILE.relative_to(BATCH_FILE.parents[2])}")

    # Summary by modality
    by_mod: dict[str, int] = {}
    for d in deduped:
        by_mod[d["modality_source"]] = by_mod.get(d["modality_source"], 0) + 1
    for m, n in sorted(by_mod.items()):
        print(f"  {m}: {n}")
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
