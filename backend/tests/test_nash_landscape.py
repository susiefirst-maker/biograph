"""NASH regression test — landscape-axis quality gate.

Per design doc §1.5 + ADR-0008. Runs against /api/landscape/nash.

Current state (Phase 0 Day 5):
  - Landscape engine does not exist yet (lands Phase 3 per ADR-0010).
  - `app.main` FastAPI app is not built yet.
  - This module SKIPS at collection time. When Phase 3 lands
    (app.main + services.landscape_engine import), the skip
    disappears and all 17 assertions start running.

Run after Phase 3:
  pytest tests/test_nash_landscape.py -v
"""

import pytest

# Module-level skip: deferred to Phase 5 alongside T1-landscape curation
# (see §7.4.6 priority list, ~13 hrs/landscape × 15 = ~5 person-weeks).
# The skip disappears automatically when app.services.landscape_engine
# is imported — no test code change needed when Phase 5 starts.
pytest.importorskip(
    "app.services.landscape_engine",
    reason="Phase 5 — landscape engine deferred (ADR-0008/0010/0011); entity API is sufficient for Humira test",
)

# Below this line runs only once Phase 3 arrives. Sketched per ADR-0008
# §"Test scaffold" so the 17 assertions are pre-declared.

from typing import Any, Callable  # noqa: E402


NASH_SLUG = "nash"

NASH_REQUIREMENTS: list[tuple[str, Callable[[dict[str, Any]], bool]]] = [
    ("disease_mechanism_overview", lambda d: bool(d.get("disease_overview")) and len(d["disease_overview"]) > 200),
    ("mechanism_map_has_thrb", lambda d: any("THR" in (m.get("class") or "") for m in d.get("mechanism_map") or [])),
    ("mechanism_map_has_fxr", lambda d: any("FXR" in (m.get("class") or "") for m in d.get("mechanism_map") or [])),
    ("mechanism_map_has_glp1", lambda d: any("GLP" in (m.get("class") or "") for m in d.get("mechanism_map") or [])),
    ("pipeline_by_phase", lambda d: bool(d.get("pipeline")) and len((d["pipeline"] or {}).get("phase_3") or []) > 0),
    ("approved_drug_resmetirom", lambda d: "resmetirom" in str(d).lower()),
    ("failed_programs_flagged", lambda d: any("selonsertib" in str(t).lower() for t in d.get("failed_trials") or [])),
    ("companies_multi", lambda d: len(d.get("companies") or []) >= 5),
    ("key_trials_maestro", lambda d: any("MAESTRO" in (t.get("name") or "") for t in d.get("key_trials") or [])),
    ("scientific_bottlenecks_present", lambda d: len(d.get("scientific_bottlenecks") or []) >= 3),
    ("market_dynamics_usd", lambda d: "$" in str(d.get("market_dynamics") or "")),
    ("regulatory_context_present", lambda d: d.get("regulatory_context") is not None),
    ("hot_targets_ranked", lambda d: len(d.get("hot_targets") or []) >= 4),
    ("literature_pubmed", lambda d: len(d.get("literature") or []) >= 3),
    ("chinese_commentary_present", lambda d: any((a.get("language") or "") == "zh" for a in d.get("articles") or d.get("chinese_commentary") or [])),
    ("applicable_lessons", lambda d: len(d.get("lessons") or []) >= 1),
    ("tier_is_t1_after_curation", lambda d: (d.get("meta") or {}).get("quality_tier") == "T1_CURATED"),
]


@pytest.fixture
async def nash_payload():
    """Hit /api/landscape/nash and return data payload. Requires FastAPI app."""
    from httpx import ASGITransport, AsyncClient

    from app.main import app

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.get(f"/api/landscape/{NASH_SLUG}?lang=en")
        assert response.status_code == 200, response.text
        body = response.json()
        return {"meta": body.get("meta"), **body.get("data", {})}


@pytest.mark.parametrize(
    "name, check",
    [pytest.param(n, c, id=n) for n, c in NASH_REQUIREMENTS],
)
async def test_nash_requirement(nash_payload, name, check):
    assert check(nash_payload), f"NASH requirement '{name}' failed. Payload: {nash_payload}"
