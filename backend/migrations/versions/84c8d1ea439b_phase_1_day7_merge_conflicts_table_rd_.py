"""phase-1-day7: merge_conflicts table + RD unique + dedup

Revision ID: 84c8d1ea439b
Revises: 41de1fbac883
Create Date: 2026-04-19 15:30:54.903610

Implements ADR-0007 — merge_conflicts audit table for per-field cross-source
provenance. Also fixes the Day 6 deferred bug: regulatory_decisions had no
unique constraint on (application_number, submission_number) and silently
duplicated under concurrent batch ingest. Dedups existing rows first, then
adds the unique index.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB


revision: str = '84c8d1ea439b'
down_revision: Union[str, Sequence[str], None] = '41de1fbac883'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""

    # 1. Dedup existing regulatory_decisions — keep earliest row per
    #    (application_number, submission_number). Day 6 batch produced
    #    duplicates silently; this preserves the first-inserted row's id.
    op.execute("""
        DELETE FROM regulatory_decisions rd
        WHERE rd.id NOT IN (
            SELECT DISTINCT ON (application_number, submission_number) id
            FROM regulatory_decisions
            ORDER BY application_number, submission_number, created_at ASC
        );
    """)

    # 2. Add composite unique index so ON CONFLICT works in the service.
    # Idempotent — prior failed downgrade runs can leave this index behind.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_regulatory_decisions_app_sub "
        "ON regulatory_decisions (application_number, submission_number);"
    )

    # 3. merge_conflicts audit table (ADR-0007).
    op.create_table(
        "merge_conflicts",
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("entity_type", sa.String(32), nullable=False),
        sa.Column("entity_id", sa.UUID(as_uuid=True), nullable=False),
        sa.Column("field_name", sa.String(128), nullable=False),
        sa.Column("field_category", sa.String(32), nullable=False),
        sa.Column("source_a", sa.String(64), nullable=False),
        sa.Column("value_a", JSONB()),
        sa.Column("source_b", sa.String(64), nullable=False),
        sa.Column("value_b", JSONB()),
        sa.Column("resolved_source", sa.String(64), nullable=False),
        sa.Column("resolved_value", JSONB()),
        sa.Column(
            "resolution_reason",
            sa.String(32),
            nullable=False,
            comment="precedence / manual_override / normalization_match / duplicate_flag",
        ),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("resolved_by", sa.String(64)),
    )
    op.create_index(
        "ix_merge_conflicts_entity",
        "merge_conflicts",
        ["entity_type", "entity_id"],
    )
    op.create_index(
        "ix_merge_conflicts_field",
        "merge_conflicts",
        ["entity_type", "field_name"],
    )
    op.create_index(
        "ix_merge_conflicts_detected",
        "merge_conflicts",
        [sa.text("detected_at DESC")],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.execute("DROP INDEX IF EXISTS ix_merge_conflicts_detected;")
    op.execute("DROP INDEX IF EXISTS ix_merge_conflicts_field;")
    op.execute("DROP INDEX IF EXISTS ix_merge_conflicts_entity;")
    op.execute("DROP TABLE IF EXISTS merge_conflicts CASCADE;")
    op.execute("DROP INDEX IF EXISTS uq_regulatory_decisions_app_sub;")
