"""Reflection-based test enforcing the `_zh` invariant from design doc §5.2.

For every entity inheriting BilingualNarrativeMixin and declaring
``__narrative_fields__``, this test asserts that every declared field
has its ``_zh`` and ``_source_refs`` sibling columns.

Per ADR-0006. Day 3+: runs over the 8 real bilingual entities (Drug,
Target, Company, Indication, ClinicalTrial, Patent, Event, Lesson).
"""

import pytest

# Importing the package registers all entities on Base.registry.
import app.models  # noqa: F401
from app.models.base import Base
from app.models.mixins import BilingualNarrativeMixin


def _bilingual_models() -> list[type]:
    """Walk Base.registry and return classes that mix in BilingualNarrativeMixin."""
    return [
        mapper.class_
        for mapper in Base.registry.mappers
        if issubclass(mapper.class_, BilingualNarrativeMixin)
    ]


@pytest.mark.parametrize(
    "model", _bilingual_models(), ids=lambda m: m.__name__
)
def test_zh_invariant(model: type) -> None:
    """Every name in __narrative_fields__ has _zh and _source_refs siblings."""
    narratives = getattr(model, "__narrative_fields__", [])
    assert narratives, (
        f"{model.__name__} inherits BilingualNarrativeMixin but declares "
        f"no __narrative_fields__. Either declare them, or remove the mixin."
    )

    missing: list[str] = []
    for field in narratives:
        for suffix in ("", "_zh", "_source_refs"):
            col = f"{field}{suffix}"
            if not hasattr(model, col):
                missing.append(f"{model.__name__}.{col}")

    assert not missing, (
        f"{model.__name__} declares narrative fields but is missing required "
        f"siblings: {missing}. Add the columns or remove the field name "
        f"from __narrative_fields__."
    )
