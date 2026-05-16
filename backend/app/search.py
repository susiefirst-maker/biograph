"""Meilisearch client + unified `entities` index.

Every searchable entity (drug/target/company/indication) lands in a single
index keyed by `{entity_type}:{id}`. Searchable attributes: display_name,
aliases — CJK tokenization is built into Meilisearch v1.6+, so "修美乐"
resolves to adalimumab without extra config.

Index layout:
    id:             "{entity_type}:{uuid}"    (Meili primary key)
    entity_type:    "drug" | "target" | "company" | "indication"
    entity_id:      "{uuid}"                   (for `link` reconstruction)
    display_name:   generic_name / gene_symbol / name
    aliases:        brand_names + aliases + name_zh + (gene variants)
    modality:       only set for drugs (nullable facet)
"""

from __future__ import annotations

from typing import Any, Iterable

import meilisearch

from app.config import settings

ENTITIES_INDEX = "entities"


def client() -> meilisearch.Client:
    return meilisearch.Client(settings.meili_url, settings.meili_master_key)


def ensure_index() -> meilisearch.index.Index:
    """Create the entities index if missing; configure attributes idempotently."""
    c = client()
    try:
        c.create_index(ENTITIES_INDEX, {"primaryKey": "id"})
    except meilisearch.errors.MeilisearchApiError as exc:
        if "index_already_exists" not in str(exc):
            raise
    index = c.index(ENTITIES_INDEX)
    index.update_settings(
        {
            "searchableAttributes": ["display_name", "aliases"],
            "filterableAttributes": ["entity_type", "modality"],
            "sortableAttributes": ["display_name"],
        }
    )
    return index


def upsert(documents: Iterable[dict[str, Any]]) -> None:
    docs = list(documents)
    if not docs:
        return
    ensure_index().add_documents(docs)


def reset_index() -> None:
    """Drop and recreate. Test-only helper — never call from prod paths."""
    c = client()
    try:
        c.delete_index(ENTITIES_INDEX)
    except meilisearch.errors.MeilisearchApiError:
        pass
    ensure_index()


def search(
    query: str,
    *,
    entity_type: str | None = None,
    limit: int = 20,
) -> list[dict[str, Any]]:
    filters = [f"entity_type = {entity_type}"] if entity_type else None
    result = ensure_index().search(
        query,
        {"limit": limit, "filter": filters},
    )
    return list(result.get("hits", []))


def entity_doc_id(entity_type: str, entity_id: str) -> str:
    # Meili document IDs must be alphanumeric, hyphens, or underscores only.
    # `drug_<uuid>` rather than `drug:<uuid>`.
    return f"{entity_type}_{entity_id}"


# ── Document shaping + full reindex ──────────────────────────────────


def drug_doc(drug) -> dict[str, Any]:
    return {
        "id": entity_doc_id("drug", str(drug.id)),
        "entity_type": "drug",
        "entity_id": str(drug.id),
        "display_name": drug.generic_name,
        "aliases": list(drug.brand_names or []) + list(drug.aliases or []),
        "modality": drug.modality,
    }


def target_doc(target) -> dict[str, Any]:
    aliases: list[str] = []
    if target.approved_name:
        aliases.append(target.approved_name)
    if target.uniprot_id:
        aliases.append(target.uniprot_id)
    if target.ensembl_id:
        aliases.append(target.ensembl_id)
    return {
        "id": entity_doc_id("target", str(target.id)),
        "entity_type": "target",
        "entity_id": str(target.id),
        "display_name": target.gene_symbol or target.approved_name or "(unknown)",
        "aliases": aliases,
        "modality": None,
    }


def company_doc(company) -> dict[str, Any]:
    aliases: list[str] = []
    if company.ticker:
        aliases.append(company.ticker)
    if company.sec_cik:
        aliases.append(company.sec_cik)
    return {
        "id": entity_doc_id("company", str(company.id)),
        "entity_type": "company",
        "entity_id": str(company.id),
        "display_name": company.name,
        "aliases": aliases,
        "modality": None,
    }


def indication_doc(indication) -> dict[str, Any]:
    aliases = list(indication.aliases or [])
    if indication.name_zh:
        aliases.append(indication.name_zh)
    if indication.efo_id:
        aliases.append(indication.efo_id)
    return {
        "id": entity_doc_id("indication", str(indication.id)),
        "entity_type": "indication",
        "entity_id": str(indication.id),
        "display_name": indication.name,
        "aliases": aliases,
        "modality": None,
    }


def reindex_all_sync(session) -> dict[str, int]:
    """Pull every searchable row from Postgres (sync session) and upsert to Meili.

    Returns per-type counts.
    """
    from app.models import Company, Drug, Indication, Target

    ensure_index()
    counts: dict[str, int] = {}

    for model, shaper, key in [
        (Drug, drug_doc, "drug"),
        (Target, target_doc, "target"),
        (Company, company_doc, "company"),
        (Indication, indication_doc, "indication"),
    ]:
        rows = session.query(model).all()
        upsert(shaper(r) for r in rows)
        counts[key] = len(rows)
    return counts
