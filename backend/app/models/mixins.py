class BilingualNarrativeMixin:
    """Marks a model as carrying bilingual narrative fields.

    Subclasses MUST declare ``__narrative_fields__: list[str]`` and provide
    three columns per declared name: ``<name>``, ``<name>_zh``, and
    ``<name>_source_refs``.

    The invariant is enforced by tests/test_models_invariants.py via
    reflection over Base.registry. Forgetting a sibling column fails the
    test suite. Per ADR-0006 / design doc §5.2.
    """

    __narrative_fields__: list[str] = []
