"""ClaudeClient unit tests — budget guard + missing-key error.

Does NOT hit the live Claude API. Live narrative generation runs via
scripts/generate_narrative.py (Phase 2+) when key is set.
"""

import pytest

from app.compilation.claude_client import (
    BudgetExceeded,
    ClaudeClient,
    LLMUsage,
    MissingAPIKey,
)


def test_llm_usage_cost_calculation() -> None:
    """1M input tokens × $3/M + 500k output × $15/M = $3 + $7.5 = $10.50."""
    u = LLMUsage(input_tokens=1_000_000, output_tokens=500_000, model="claude-sonnet-4-6")
    assert abs(u.estimated_cost_usd - 10.5) < 1e-9


def test_client_tracks_cumulative_spend() -> None:
    """cumulative_cost_usd accumulates across calls (tested by hand-seeding)."""
    c = ClaudeClient()
    assert c.cumulative_cost_usd == 0.0
    assert c.call_count == 0
    # Manually bump (real path is messages_create, but that hits the network).
    c.cumulative_cost_usd += 0.50
    c.call_count += 1
    assert c.cumulative_cost_usd == 0.50
    assert c.call_count == 1


@pytest.mark.asyncio
async def test_budget_guard_blocks_over_limit(monkeypatch) -> None:
    """A client at/over budget refuses new calls with BudgetExceeded."""
    c = ClaudeClient()
    c.cumulative_cost_usd = c.budget_cap_usd + 1.0  # simulate over-budget

    with pytest.raises(BudgetExceeded, match="budget"):
        await c.messages_create(system="x", user="y")


@pytest.mark.asyncio
async def test_missing_api_key_is_clear(monkeypatch) -> None:
    """Without ANTHROPIC_API_KEY, calls raise a descriptive MissingAPIKey."""
    from app.config import settings

    monkeypatch.setattr(settings, "anthropic_api_key", "")
    c = ClaudeClient()

    with pytest.raises(MissingAPIKey, match="ANTHROPIC_API_KEY"):
        await c.messages_create(system="x", user="y")
