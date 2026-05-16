"""App configuration loaded from .env via pydantic-settings.

Single source of truth for env vars at runtime. See .env.example at repo
root for the full catalog.
"""

from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


REPO_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=REPO_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Database (async for app, sync for migrations) ───────────────────
    database_url: str = Field(default="postgresql+asyncpg://biograph:biograph_dev@localhost:5432/biograph")
    database_url_sync: str = Field(default="postgresql+psycopg2://biograph:biograph_dev@localhost:5432/biograph")

    # ── Meilisearch ─────────────────────────────────────────────────────
    meili_url: str = Field(default="http://localhost:7700")
    meili_master_key: str = Field(default="biograph_dev_key")

    # ── Redis (Celery broker) ──────────────────────────────────────────
    redis_url: str = Field(default="redis://localhost:6379/0")

    # ── Anthropic (offline narrative compilation only) ────────────────
    anthropic_api_key: str = Field(default="")
    anthropic_model: str = Field(default="claude-sonnet-4-6")
    anthropic_max_spend_usd: float = Field(default=50.0)

    # ── External scientific APIs ───────────────────────────────────────
    open_targets_url: str = Field(default="https://api.platform.opentargets.org/api/v4/graphql")
    clinical_trials_url: str = Field(default="https://clinicaltrials.gov/api/v2")
    fda_url: str = Field(default="https://api.fda.gov")
    sec_user_agent: str = Field(default="BioGraph/0.1 (local-dev)")
    pubmed_api_key: str = Field(default="")
    drugbank_api_key: str = Field(default="")
    patentsview_api_key: str = Field(default="")

    # ── Ops guards ─────────────────────────────────────────────────────
    llm_per_call_max_tokens: int = Field(default=4000)

    # ── Deploy-only ─────────────────────────────────────────────────────
    # Comma-separated allowed CORS origins. Defaults to localhost dev
    # ports; override in prod (e.g. CORS_ORIGINS="https://biograph.app").
    cors_origins: str = Field(
        default="http://localhost:3000,http://127.0.0.1:3000"
    )
    # Optional regex (e.g. `https://.*\.trycloudflare\.com`) for preview
    # deploys where the hostname is dynamic. Empty = disabled.
    cors_origin_regex: str = Field(default="")

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
