"""BaseIngester ABC — every data-source ingester implements this interface.

Per design doc §6.1. Contract:

    raw = await ingester.fetch_raw(identifier)   # external API call
    normalized = ingester.normalize(raw)          # map to BioGraph schema
    errors = ingester.validate(normalized)        # data-integrity check
    if errors: raise ValidationError(errors)
    return normalized

Subclasses:
  - OpenTargetsIngester (Day 4)
  - DrugBankIngester, ClinicalTrialsIngester, FDAIngester, SECIngester (Phase 1)
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from app.config import REPO_ROOT


class ValidationError(Exception):
    """Raised by BaseIngester.ingest when validate() returns non-empty errors."""

    def __init__(self, errors: list[str]) -> None:
        self.errors = errors
        super().__init__("; ".join(errors))


class BaseIngester(ABC):
    """All ingesters implement this interface."""

    #: Short identifier for the source (e.g., "open_targets", "drugbank").
    #: Used in source_refs and merge_conflicts.source_a/source_b.
    source_name: str = ""

    @abstractmethod
    async def fetch_raw(self, identifier: str) -> dict[str, Any]:
        """Fetch raw data from external API. Returns raw JSON dict."""

    @abstractmethod
    def normalize(self, raw: dict[str, Any]) -> dict[str, Any]:
        """Map a raw API response to BioGraph schema fields."""

    @abstractmethod
    def validate(self, normalized: dict[str, Any]) -> list[str]:
        """Return list of validation errors. Empty list means valid."""

    async def ingest(self, identifier: str) -> dict[str, Any]:
        """Full pipeline: fetch → normalize → validate → return."""
        raw = await self.fetch_raw(identifier)
        self._save_raw(identifier, raw)
        normalized = self.normalize(raw)
        errors = self.validate(normalized)
        if errors:
            raise ValidationError(errors)
        return normalized

    # Raw-payload cache — data/raw/<source>/<identifier>.json
    # Enables replay for testing (design doc §6.2.1 acceptance criterion).
    def _save_raw(self, identifier: str, raw: dict[str, Any]) -> None:
        if not self.source_name:
            return
        import json

        outdir = REPO_ROOT / "data" / "raw" / self.source_name
        outdir.mkdir(parents=True, exist_ok=True)
        safe_id = identifier.replace("/", "_")
        (outdir / f"{safe_id}.json").write_text(json.dumps(raw, indent=2, default=str))
