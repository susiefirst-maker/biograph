"""Shared route dependencies + helpers."""

from typing import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session


async def db() -> AsyncIterator[AsyncSession]:
    async with get_session() as session:
        yield session


def sources_from_provenance(provenance: dict) -> list[str]:
    if not provenance:
        return []
    sources: set[str] = set()
    for field_meta in provenance.values():
        if isinstance(field_meta, dict) and (src := field_meta.get("source")):
            sources.add(str(src))
    return sorted(sources)
