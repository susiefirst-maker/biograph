"""Curated lessons loader — applies data/curated/<drug>_lessons.yml.

Lessons are bilingual (pattern + pattern_zh per ADR-0006). Natural key:
(title, lesson_type). Linked to Drug via polymorphic entity_lesson_link.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml
from sqlalchemy import and_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Drug, Lesson
from app.models._helpers import LessonType
from app.models.relationships import entity_lesson_link


CURATED_DIR = Path(__file__).resolve().parents[3] / "data" / "curated"
LESSON_FILES = sorted(CURATED_DIR.glob("*_lessons.yml"))


def load_curated_lessons() -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for path in LESSON_FILES:
        if not path.exists():
            continue
        doc = yaml.safe_load(path.read_text()) or {}
        out.extend(doc.get("drugs") or [])
    return out


async def apply_curated_lessons(session: AsyncSession) -> int:
    """Upsert Lesson rows + link via entity_lesson_link. Returns count."""
    entries = load_curated_lessons()
    total = 0

    for drug_entry in entries:
        chembl_id = drug_entry.get("chembl_id")
        lessons = drug_entry.get("lessons") or []
        if not chembl_id or not lessons:
            continue

        drug = await session.scalar(select(Drug).where(Drug.chembl_id == chembl_id))
        if drug is None:
            continue

        for l in lessons:
            title = l.get("title")
            if not title:
                continue
            try:
                lesson_type = LessonType(l["lesson_type"].lower())
            except (ValueError, KeyError):
                continue

            existing = await session.scalar(
                select(Lesson).where(
                    and_(
                        Lesson.title == title,
                        Lesson.lesson_type == lesson_type,
                    )
                )
            )

            if existing is None:
                lesson = Lesson(
                    title=title,
                    title_zh=l.get("title_zh"),
                    lesson_type=lesson_type,
                    pattern=l.get("pattern"),
                    pattern_zh=l.get("pattern_zh"),
                    pattern_source_refs=[],
                    key_evidence=[{"text": e} for e in (l.get("key_evidence") or [])],
                    limitations=l.get("limitations") or [],
                    applicable_contexts=l.get("applicable_contexts") or [],
                    applicable_to_landscapes=l.get("applicable_to_landscapes") or [],
                    human_reviewed=bool(l.get("human_reviewed")),
                    reviewed_by=l.get("reviewed_by"),
                    reviewed_at=datetime.utcnow() if l.get("human_reviewed") else None,
                    field_provenance={"_curated_source": "data/curated/humira_lessons.yml"},
                )
                session.add(lesson)
                await session.flush()
                lesson_id = lesson.id
                total += 1
            else:
                # Update mutable fields; preserve identity
                existing.pattern = l.get("pattern") or existing.pattern
                existing.pattern_zh = l.get("pattern_zh") or existing.pattern_zh
                if l.get("limitations"):
                    existing.limitations = l["limitations"]
                if l.get("applicable_contexts"):
                    existing.applicable_contexts = l["applicable_contexts"]
                lesson_id = existing.id

            # Link Lesson → Drug via polymorphic junction
            stmt = pg_insert(entity_lesson_link).values(
                lesson_id=lesson_id,
                entity_type="drug",
                entity_id=drug.id,
            )
            stmt = stmt.on_conflict_do_nothing(
                index_elements=["lesson_id", "entity_type", "entity_id"]
            )
            await session.execute(stmt)

    await session.flush()
    return total
