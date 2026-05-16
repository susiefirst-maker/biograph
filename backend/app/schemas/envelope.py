"""ADR-0004 response envelope: every handler returns {data, meta, related}.

`EntityEnvelope[T]` is generic over the entity payload type. `related` is
an untyped chip map — each chip has at minimum `id`, `link`, and a
display field, but the exact shape varies per entity type.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel, ConfigDict

T = TypeVar("T")


class EntityMeta(BaseModel):
    entity_type: str
    version: int
    last_verified_at: datetime | None = None
    sources: list[str] = []
    narrative_generated_at: datetime | None = None
    lang_fallback: bool = False


class EntityEnvelope(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: T
    meta: EntityMeta
    related: dict[str, list[dict[str, Any]]] = {}


class ListMeta(BaseModel):
    count: int
    entity_type: str


class ListEnvelope(BaseModel, Generic[T]):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    data: list[T]
    meta: ListMeta
    related: dict[str, list[dict[str, Any]]] = {}


class ErrorBody(BaseModel):
    code: str
    message: str
    details: dict[str, Any] = {}


class ErrorEnvelope(BaseModel):
    error: ErrorBody
