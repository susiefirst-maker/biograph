"""QA gate checker for local and CI data-integrity checks.

Runs data-integrity and completeness assertions against the current PostgreSQL
state. Exits 0 when all checks pass, non-zero on any failure.

Default gate:
  - Alembic is at head.
  - 18 expected tables present + entity_relationships view.
  - adalimumab ingested with TNF target and ≥10 indications.
  - entity_relationships view returns edges (matches junction counts × 2).
  - Orphan-drug ratio is checked for large seeded datasets.
  - Narrative invariant: every bilingual model's _zh columns physically present.

Run:
  PYTHONPATH=. python scripts/qa_check.py --phase 0
"""

import argparse
import subprocess
import sys
from typing import Callable

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.engine import Engine

from app.config import settings
from app.models import Base, BilingualNarrativeMixin


EXPECTED_PHASE_0_TABLES = {
    "alembic_version",
    "articles",
    "claims",
    "clinical_trials",
    "companies",
    "drug_indication_link",
    "drug_target_link",
    "drugs",
    "entity_claim_link",
    "entity_lesson_link",
    "event_entity_link",
    "events",
    "indications",
    "lessons",
    "patents",
    "regulatory_decisions",
    "target_indication_link",
    "targets",
}


class CheckResult:
    def __init__(self, name: str, ok: bool, detail: str = "") -> None:
        self.name = name
        self.ok = ok
        self.detail = detail

    def format(self) -> str:
        mark = "✔" if self.ok else "✘"
        line = f"  {mark} {self.name}"
        if self.detail:
            line += f"  — {self.detail}"
        return line


def check_alembic_head() -> CheckResult:
    proc = subprocess.run(
        ["alembic", "current"],
        capture_output=True,
        text=True,
        cwd=str((__import__("pathlib").Path(__file__).resolve().parent.parent)),
    )
    ok = proc.returncode == 0 and "(head)" in proc.stdout
    return CheckResult("alembic at head", ok, (proc.stdout + proc.stderr).strip().splitlines()[-1] if proc.stdout or proc.stderr else "")


def check_tables_present(engine: Engine) -> CheckResult:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    missing = EXPECTED_PHASE_0_TABLES - tables
    extra = tables - EXPECTED_PHASE_0_TABLES
    ok = not missing
    detail = f"{len(tables)} tables"
    if missing:
        detail += f"; MISSING: {sorted(missing)}"
    if extra:
        detail += f"; extra: {sorted(extra)}"
    return CheckResult("all expected tables present", ok, detail)


def check_view_present(engine: Engine) -> CheckResult:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT 1 FROM information_schema.views WHERE table_name = 'entity_relationships'")).fetchall()
    return CheckResult("entity_relationships VIEW exists", bool(rows))


def check_adalimumab_ingested(engine: Engine) -> CheckResult:
    with engine.connect() as conn:
        row = conn.execute(text("SELECT id, generic_name FROM drugs WHERE chembl_id = 'CHEMBL1201580'")).fetchone()
    if not row:
        return CheckResult(
            "adalimumab (CHEMBL1201580) ingested",
            False,
            "not found — run `python scripts/ingest_adalimumab.py`",
        )
    return CheckResult("adalimumab (CHEMBL1201580) ingested", True, f"drug_id={row.id}")


def check_humira_has_tnf_target(engine: Engine) -> CheckResult:
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                """
                SELECT t.gene_symbol
                  FROM drugs d
                  JOIN drug_target_link l ON l.drug_id = d.id
                  JOIN targets t ON t.id = l.target_id
                 WHERE d.chembl_id = 'CHEMBL1201580'
                """
            )
        ).fetchall()
    symbols = [r.gene_symbol for r in rows]
    ok = any((s or "").startswith("TNF") for s in symbols)
    return CheckResult("Humira → TNF target linked", ok, f"targets: {symbols}")


def check_humira_has_indications(engine: Engine, min_count: int = 10) -> CheckResult:
    with engine.connect() as conn:
        row = conn.execute(
            text(
                """
                SELECT COUNT(*) AS n
                  FROM drugs d
                  JOIN drug_indication_link l ON l.drug_id = d.id
                 WHERE d.chembl_id = 'CHEMBL1201580'
                """
            )
        ).fetchone()
    count = row.n if row else 0
    return CheckResult(
        f"Humira → ≥{min_count} indications",
        count >= min_count,
        f"count={count}",
    )


def check_entity_relationships_view(engine: Engine) -> CheckResult:
    with engine.connect() as conn:
        rel_count = conn.execute(text("SELECT COUNT(*) FROM entity_relationships")).scalar() or 0
        dt = conn.execute(text("SELECT COUNT(*) FROM drug_target_link")).scalar() or 0
        di = conn.execute(text("SELECT COUNT(*) FROM drug_indication_link")).scalar() or 0
    expected_lower_bound = (dt + di) * 2  # forward + reverse edges from these two junctions
    ok = rel_count >= expected_lower_bound
    return CheckResult(
        "entity_relationships view populated",
        ok,
        f"view={rel_count}, drug_target×2={dt * 2}, drug_indication×2={di * 2}",
    )


def check_no_orphan_drugs(engine: Engine) -> CheckResult:
    """Drugs without a single target or indication link. Some orphan drugs are
    expected in small offline fixture seeds. Enforce the 5% threshold only when
    the database is large enough for that ratio to be meaningful."""
    with engine.connect() as conn:
        total = conn.execute(text("SELECT COUNT(*) FROM drugs")).scalar() or 0
        orphans = conn.execute(
            text(
                """
                SELECT COUNT(*) FROM drugs d
                WHERE NOT EXISTS (SELECT 1 FROM drug_target_link l WHERE l.drug_id = d.id)
                  AND NOT EXISTS (SELECT 1 FROM drug_indication_link l WHERE l.drug_id = d.id)
                """
            )
        ).scalar() or 0
    if total < 50:
        return CheckResult(
            "orphan drugs ratio",
            True,
            f"fixture seed: orphans={orphans}/{total}; threshold enforced at total>=50",
        )
    ratio_ok = total == 0 or (orphans / total) <= 0.05
    return CheckResult(
        "orphan drugs ratio",
        ratio_ok,
        f"orphans={orphans}/{total} ({(orphans / total * 100) if total else 0:.1f}%)",
    )


def check_bilingual_invariant() -> CheckResult:
    """Each BilingualNarrativeMixin class has _zh and _source_refs siblings for every declared narrative field."""
    missing: list[str] = []
    for mapper in Base.registry.mappers:
        cls = mapper.class_
        if not issubclass(cls, BilingualNarrativeMixin):
            continue
        for field in getattr(cls, "__narrative_fields__", []):
            for suffix in ("", "_zh", "_source_refs"):
                if not hasattr(cls, f"{field}{suffix}"):
                    missing.append(f"{cls.__name__}.{field}{suffix}")
    return CheckResult(
        "bilingual invariant",
        not missing,
        f"missing: {missing}" if missing else "all _zh + _source_refs siblings present",
    )


PHASE_0_CHECKS: list[Callable[..., CheckResult]] = [
    check_alembic_head,
    check_tables_present,
    check_view_present,
    check_adalimumab_ingested,
    check_humira_has_tnf_target,
    check_humira_has_indications,
    check_entity_relationships_view,
    check_no_orphan_drugs,
    check_bilingual_invariant,
]


def run_phase_0(engine: Engine) -> list[CheckResult]:
    results: list[CheckResult] = []
    for fn in PHASE_0_CHECKS:
        try:
            if "engine" in fn.__code__.co_varnames:
                result = fn(engine)
            else:
                result = fn()
        except Exception as exc:  # noqa: BLE001 — surface any unexpected failure to the operator
            result = CheckResult(fn.__name__, False, f"exception: {exc!r}")
        results.append(result)
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="BioGraph QA gate checker")
    parser.add_argument("--phase", type=int, default=0, choices=[0], help="Gate profile to check")
    args = parser.parse_args()

    print(f"BioGraph QA gate profile {args.phase}")
    print("=" * 60)

    engine = create_engine(settings.database_url_sync)
    if args.phase == 0:
        results = run_phase_0(engine)
    else:  # pragma: no cover
        print(f"Gate profile {args.phase} checks not implemented yet.")
        return 2

    for r in results:
        print(r.format())

    failed = [r for r in results if not r.ok]
    print("=" * 60)
    if failed:
        print(f"FAIL: {len(failed)} of {len(results)} checks failed")
        return 1
    print(f"PASS: all {len(results)} checks green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
