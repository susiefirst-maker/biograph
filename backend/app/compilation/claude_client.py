"""Thin wrapper over Anthropic's Claude SDK with budget and token guards.

Budget: ANTHROPIC_MAX_SPEND_USD env gate. Token budget: LLM_PER_CALL_MAX_TOKENS.
"""

from dataclasses import dataclass

from app.config import settings


# Per 2026-04 Anthropic published pricing for claude-sonnet-4-6 (USD per 1M tokens).
# Update when pricing changes; affects budget guard only, not correctness.
PRICE_INPUT_PER_1M = 3.0
PRICE_OUTPUT_PER_1M = 15.0


@dataclass
class LLMUsage:
    input_tokens: int
    output_tokens: int
    model: str

    @property
    def estimated_cost_usd(self) -> float:
        return (
            (self.input_tokens / 1_000_000) * PRICE_INPUT_PER_1M
            + (self.output_tokens / 1_000_000) * PRICE_OUTPUT_PER_1M
        )


class BudgetExceeded(RuntimeError):
    pass


class MissingAPIKey(RuntimeError):
    pass


class ClaudeClient:
    """Async Claude wrapper with cumulative-spend tracking.

    Create one per process; it tracks spend across calls. The budget guard
    refuses new calls once cumulative cost crosses ANTHROPIC_MAX_SPEND_USD.
    """

    def __init__(self, model: str | None = None, max_tokens_per_call: int | None = None) -> None:
        self.model = model or settings.anthropic_model
        self.max_tokens_per_call = max_tokens_per_call or settings.llm_per_call_max_tokens
        self.budget_cap_usd = settings.anthropic_max_spend_usd
        self.cumulative_cost_usd = 0.0
        self.call_count = 0
        self._sdk_client = None

    def _lazy_init_sdk(self) -> None:
        if self._sdk_client is not None:
            return
        if not settings.anthropic_api_key:
            raise MissingAPIKey(
                "ANTHROPIC_API_KEY not set. Add to .env and reload. "
                "LLM calls are used for offline narrative-compilation workflows, "
                "not request-time API handlers."
            )
        # Lazy import so the SDK isn't required at module-import time
        # (e.g., for tests or when the key isn't set).
        from anthropic import AsyncAnthropic

        self._sdk_client = AsyncAnthropic(api_key=settings.anthropic_api_key)

    async def messages_create(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
    ) -> tuple[str, LLMUsage]:
        """Return (text, usage). Enforces budget and token caps."""
        if self.cumulative_cost_usd >= self.budget_cap_usd:
            raise BudgetExceeded(
                f"Cumulative LLM spend ${self.cumulative_cost_usd:.2f} "
                f"has hit the ${self.budget_cap_usd:.2f} budget. "
                "Raise ANTHROPIC_MAX_SPEND_USD in .env or investigate."
            )

        self._lazy_init_sdk()
        assert self._sdk_client is not None

        response = await self._sdk_client.messages.create(
            model=self.model,
            max_tokens=max_tokens or self.max_tokens_per_call,
            system=system,
            messages=[{"role": "user", "content": user}],
        )

        # Extract text from first content block (Claude SDK shape)
        text = ""
        if response.content:
            text = response.content[0].text

        usage = LLMUsage(
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            model=self.model,
        )
        self.cumulative_cost_usd += usage.estimated_cost_usd
        self.call_count += 1

        return text, usage
