"""Curated event-timeline loader — applies data/curated/humira_events.yml
(and future <drug>_events.yml) into Event + event_entity_link rows.

Supports causal chains: an event's `triggered_by` field names another
event's `id_slug`; loader resolves slugs → UUIDs in a second pass.
"""

from datetime import date, datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Drug, Event
from app.models.relationships import event_entity_link


CURATED_DIR = Path(__file__).resolve().parents[3] / "data" / "curated"
EVENTS_FILES = sorted(CURATED_DIR.glob("*_events.yml"))


def _parse_date(raw: Any) -> date | None:
    if isinstance(raw, date):
        return raw
    if not raw:
        return None
    try:
        return datetime.strptime(str(raw), "%Y-%m-%d").date()
    except ValueError:
        return None


def load_event_files() -> list[dict[str, Any]]:
    """Concatenate curated event YAMLs into one drug-keyed list."""
    out: list[dict[str, Any]] = []
    for path in EVENTS_FILES:
        if not path.exists():
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        out.extend(doc.get("drugs") or [])
    return out


async def apply_curated_events(session: AsyncSession) -> int:
    """Apply all curated event files. Returns count of events persisted.

    Two-pass because triggered_by references other events by id_slug:
      Pass 1 — upsert Event rows, collect slug → UUID map.
      Pass 2 — set Event.triggered_by via slug lookup.
    """
    entries = load_event_files()
    total_applied = 0

    for drug_entry in entries:
        chembl_id = drug_entry.get("chembl_id")
        events = drug_entry.get("events") or []
        if not chembl_id or not events:
            continue

        drug = await session.scalar(select(Drug).where(Drug.chembl_id == chembl_id))
        if drug is None:
            continue

        # Pass 1: upsert events, collect slug map
        slug_to_id: dict[str, Any] = {}
        for e in events:
            slug = e.get("id_slug")
            headline = e.get("headline")
            event_type = e.get("event_type") or "unspecified"
            event_date = _parse_date(e.get("event_date"))
            if not slug or not headline:
                continue

            # Natural key for curated events: (event_type, event_date, headline)
            existing = await session.scalar(
                select(Event).where(
                    and_(
                        Event.event_type == event_type,
                        Event.event_date == event_date,
                        Event.headline == headline,
                    )
                )
            )

            if existing is None:
                row = Event(
                    event_type=event_type,
                    event_date=event_date,
                    headline=headline,
                    significance=e.get("significance"),
                    description=e.get("description"),
                    description_source_refs=e.get("source_refs") or [],
                    field_provenance={"_curated_source": "data/curated/humira_events.yml"},
                )
                session.add(row)
                await session.flush()
                slug_to_id[slug] = row.id
                total_applied += 1
            else:
                # Update mutable fields
                existing.description = e.get("description") or existing.description
                if e.get("source_refs"):
                    existing.description_source_refs = e["source_refs"]
                slug_to_id[slug] = existing.id

            # Link Event → Drug via polymorphic event_entity_link
            stmt = pg_insert(event_entity_link).values(
                event_id=slug_to_id[slug],
                entity_type="drug",
                entity_id=drug.id,
                role="subject",
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["event_id", "entity_type", "entity_id"]
            )
            await session.execute(stmt)

        # Pass 2: resolve triggered_by slugs to UUIDs
        for e in events:
            slug = e.get("id_slug")
            trigger_slug = e.get("triggered_by")
            if not slug or not trigger_slug:
                continue
            src_id = slug_to_id.get(slug)
            trg_id = slug_to_id.get(trigger_slug)
            if src_id is None or trg_id is None:
                continue
            # Load and set
            event_row = await session.scalar(select(Event).where(Event.id == src_id))
            if event_row is not None and event_row.triggered_by != trg_id:
                event_row.triggered_by = trg_id

    await session.flush()
    return total_applied
