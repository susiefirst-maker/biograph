"""Landscape engine — resolves a slug to a curator-compiled landscape.

Phase 5 / P5-D4: T1-only. Loads `data/landscapes/{slug}.yml` and
returns the parsed dict verbatim (with tier assignment). T2/T3
auto-compile via Open Targets / CT.gov / PubMed fanout is future work
(see ADR-0010 §Tier semantics).

Slug canonicalization follows ADR-0010 Decision 3 — lowercase,
non-alphanumerics collapsed to single dashes, boundary dashes stripped.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

LANDSCAPES_DIR = Path(__file__).resolve().parents[3] / "data" / "landscapes"


def canonicalize_slug(raw: str) -> str:
    """ADR-0010 Decision 3 slug rule. 'PD-1/PD-L1' → 'pd1-pdl1'."""
    lowered = raw.lower()
    collapsed = re.sub(r"[^a-z0-9]+", "-", lowered)
    return collapsed.strip("-")


def _resolve_path(slug: str) -> Path | None:
    """Direct slug match first; fall back to alias scan over all YAMLs."""
    canonical = canonicalize_slug(slug)
    direct = LANDSCAPES_DIR / f"{canonical}.yml"
    if direct.exists():
        return direct

    # Alias scan — aliases live inside each landscape file.
    if not LANDSCAPES_DIR.exists():
        return None
    for path in LANDSCAPES_DIR.glob("*.yml"):
        try:
            doc = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if not isinstance(doc, dict):
            continue
        for alias in doc.get("aliases", []) or []:
            if canonicalize_slug(alias) == canonical:
                return path
    return None


def load_landscape(slug: str) -> dict[str, Any] | None:
    """Return the parsed landscape dict, or None if slug unknown."""
    path = _resolve_path(slug)
    if path is None:
        return None
    doc = yaml.safe_load(path.read_text())
    if not isinstance(doc, dict):
        return None
    return doc


def list_curated_slugs() -> list[str]:
    """Slugs of all T1-curated landscapes on disk. Useful for admin UI."""
    if not LANDSCAPES_DIR.exists():
        return []
    return sorted(p.stem for p in LANDSCAPES_DIR.glob("*.yml"))


def _landscape_drugs(doc: dict[str, Any]) -> set[str]:
    """Normalized (lowercased, stripped) drug names across mechanism_map,
    pipeline, and key_trials — used for auto-relatedness scoring.
    Combo strings like "A + B" decompose into {a, b} so cross-class
    combinations surface overlap with both component landscapes."""
    names: set[str] = set()

    def _add(raw: str) -> None:
        # Normalize first (strips brand parentheticals + lowercase), then
        # split on combo separators. Order matters: without parens we no
        # longer have "Daiichi / AstraZeneca" sub-strings to false-split.
        normalized = _normalize_drug_name(raw)
        for part in _split_combo(normalized):
            names.add(part)

    for group in doc.get("mechanism_map", []) or []:
        for drug in group.get("drugs", []) or []:
            if name := drug.get("name"):
                _add(name)
    pipeline = doc.get("pipeline") or {}
    for phase_drugs in pipeline.values():
        for raw in phase_drugs or []:
            _add(str(raw))
    for trial in doc.get("key_trials", []) or []:
        if drug := trial.get("drug"):
            _add(drug)
    names.discard("")
    return names


def _split_combo(raw: str) -> list[str]:
    """Split a (post-normalized) drug string on combo separators —
    "A + B", "A and B", "A / B". All three imply cross-mechanism
    combination therapy that should match each component separately."""
    s = raw.replace(" and ", "+").replace("/", "+")
    return [p.strip() for p in s.split("+") if p.strip()]


def _landscape_targets(doc: dict[str, Any]) -> set[str]:
    """Hot-target gene symbols, uppercased."""
    return {
        str(t.get("gene_symbol") or "").strip().upper()
        for t in doc.get("hot_targets", []) or []
    } - {""}


def _normalize_drug_name(raw: str) -> str:
    """Strip brand-name parentheticals + lowercase for fuzzy comparison.
    "semaglutide (Ozempic / Wegovy / Rybelsus)" → "semaglutide".
    """
    s = raw.lower().strip()
    if "(" in s:
        s = s.split("(", 1)[0].strip()
    if "," in s:
        s = s.split(",", 1)[0].strip()
    return s


def derive_related(slug: str, limit: int = 5) -> list[dict[str, Any]]:
    """Auto-derive landscapes related to `slug` by drug + target overlap.

    ADR-0010 Decision 5 canonical thresholds are ≥5 shared drugs OR ≥3
    shared targets; at current curated scale (2 landscapes) those are
    too strict, so we surface any overlap ≥1 and sort by total overlap.
    Curators can freeze a specific list into the YAML later once the
    catalog grows past ~10 landscapes.
    """
    root = load_landscape(slug)
    if root is None:
        return []
    root_slug = root.get("slug", canonicalize_slug(slug))
    root_drugs = _landscape_drugs(root)
    root_targets = _landscape_targets(root)

    scored: list[dict[str, Any]] = []
    for other_slug in list_curated_slugs():
        if other_slug == root_slug:
            continue
        other = load_landscape(other_slug)
        if other is None:
            continue
        shared_drugs = root_drugs & _landscape_drugs(other)
        shared_targets = root_targets & _landscape_targets(other)
        total = len(shared_drugs) + len(shared_targets)
        if total == 0:
            continue
        scored.append(
            {
                "slug": other_slug,
                "display_name": other.get("display_name", other_slug),
                "shared_drugs": sorted(shared_drugs),
                "shared_targets": sorted(shared_targets),
                "overlap_score": total,
            }
        )

    scored.sort(key=lambda x: x["overlap_score"], reverse=True)
    return scored[:limit]
