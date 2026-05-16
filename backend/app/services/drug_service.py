"""Drug persistence — idempotent upserts keyed by chembl_id.

Phase 0 scope: single-source upsert (Open Targets). Phase 1 adds the merge
layer (ADR-0007) so multiple sources can write to the same drug record
without trampling each other.
"""

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Drug, Indication, Target
from app.models.relationships import drug_indication_link, drug_target_link


async def upsert_target(session: AsyncSession, payload: dict[str, Any]) -> Target:
    """Insert or fetch a Target by ensembl_id. Race-safe via ON CONFLICT."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    ensembl_id = payload["ensembl_id"]
    stmt = pg_insert(Target).values(
        ensembl_id=ensembl_id,
        gene_symbol=payload.get("gene_symbol"),
        approved_name=payload.get("approved_name"),
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=["ensembl_id"],
        set_={
            "gene_symbol": stmt.excluded.gene_symbol,
            "approved_name": stmt.excluded.approved_name,
        },
    )
    await session.execute(stmt)
    await session.flush()
    return await session.scalar(select(Target).where(Target.ensembl_id == ensembl_id))


async def upsert_indication(session: AsyncSession, payload: dict[str, Any]) -> Indication:
    """Insert or fetch an Indication by efo_id. Race-safe via ON CONFLICT."""
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    efo_id = payload["efo_id"]
    stmt = pg_insert(Indication).values(
        efo_id=efo_id,
        name=payload.get("name") or "(unknown)",
    )
    # Keep existing name when already set (don't overwrite with payload)
    from sqlalchemy import func
    stmt = stmt.on_conflict_do_update(
        index_elements=["efo_id"],
        set_={"name": func.coalesce(Indication.name, stmt.excluded.name)},
    )
    await session.execute(stmt)
    await session.flush()
    return await session.scalar(select(Indication).where(Indication.efo_id == efo_id))


OPEN_TARGETS_SOURCE = "open_targets"


async def upsert_drug_from_open_targets(
    session: AsyncSession, normalized: dict[str, Any]
) -> Drug:
    """Persist a normalized Open Targets payload into Drug + Target + Indication tables.

    Idempotent: repeated calls with the same chembl_id update in place.

    D-011: stamps `Drug.field_provenance[field] = "open_targets"` for
    each field written so MergeService.record_conflict can cite a real
    prior source (not `"unknown_ingester"`).
    """
    drug_payload = normalized["drug"]
    chembl_id = drug_payload["chembl_id"]

    # Fields this ingester owns. Keep in sync with the writes below.
    owned_fields = (
        "generic_name",
        "aliases",
        "brand_names",
        "modality",
        "max_phase",
        "status",
        "mechanism_of_action",
    )
    provenance_stamp = {f: {"source": OPEN_TARGETS_SOURCE} for f in owned_fields}

    existing = await session.scalar(select(Drug).where(Drug.chembl_id == chembl_id))
    if existing is None:
        drug = Drug(
            chembl_id=chembl_id,
            generic_name=drug_payload["generic_name"],
            aliases=drug_payload.get("aliases") or [],
            brand_names=drug_payload.get("brand_names") or [],
            modality=drug_payload.get("modality"),
            max_phase=drug_payload.get("max_phase"),
            status=drug_payload.get("status", "investigational"),
            mechanism_of_action=drug_payload.get("mechanism_of_action"),
            mechanism_of_action_source_refs=["opentargets:" + chembl_id]
            if drug_payload.get("mechanism_of_action")
            else [],
            field_provenance=provenance_stamp,
        )
        session.add(drug)
        await session.flush()
    else:
        drug = existing
        # Update fields per single-source (Open Targets) provenance
        drug.generic_name = drug_payload["generic_name"]
        drug.aliases = drug_payload.get("aliases") or []
        drug.brand_names = drug_payload.get("brand_names") or []
        drug.modality = drug_payload.get("modality") or drug.modality
        drug.max_phase = drug_payload.get("max_phase") or drug.max_phase
        drug.status = drug_payload.get("status") or drug.status
        if drug_payload.get("mechanism_of_action"):
            drug.mechanism_of_action = drug_payload["mechanism_of_action"]
            if "opentargets:" + chembl_id not in drug.mechanism_of_action_source_refs:
                drug.mechanism_of_action_source_refs = [
                    *drug.mechanism_of_action_source_refs,
                    "opentargets:" + chembl_id,
                ]
        # Merge provenance — don't clobber stamps from curated loaders.
        drug.field_provenance = {**(drug.field_provenance or {}), **provenance_stamp}

    # Targets: upsert + link (delete stale links is Phase 1 concern)
    target_ids: list[UUID] = []
    for t_payload in normalized.get("targets", []):
        if not t_payload.get("ensembl_id"):
            continue
        target = await upsert_target(session, t_payload)
        target_ids.append(target.id)

    await _link_many_to_many(
        session,
        drug_target_link,
        left_col="drug_id",
        right_col="target_id",
        left_id=drug.id,
        right_ids=target_ids,
    )

    # Indications: upsert + link
    indication_ids: list[UUID] = []
    for i_payload in normalized.get("indications", []):
        if not i_payload.get("efo_id"):
            continue
        indication = await upsert_indication(session, i_payload)
        indication_ids.append(indication.id)

    await _link_many_to_many(
        session,
        drug_indication_link,
        left_col="drug_id",
        right_col="indication_id",
        left_id=drug.id,
        right_ids=indication_ids,
    )

    return drug


async def _link_many_to_many(
    session: AsyncSession,
    table,
    *,
    left_col: str,
    right_col: str,
    left_id: UUID,
    right_ids: list[UUID],
) -> None:
    """Idempotently ensure (left_id, right_id) rows exist in the junction table."""
    if not right_ids:
        return

    from sqlalchemy.dialects.postgresql import insert

    rows = [{left_col: left_id, right_col: rid} for rid in right_ids]
    stmt = insert(table).values(rows).on_conflict_do_nothing(
        index_elements=[left_col, right_col]
    )
    await session.execute(stmt)
