"""p2-d2: widen claims.evidence_basis String(128) -> Text

Revision ID: 896317a30382
Revises: adbd97c20143
Create Date: 2026-04-19 20:31:56.501913

Curated Humira evidence_basis strings are ~160+ chars (citations with
source titles + dates). Bump column to Text.

Autogen initially flagged Day-7 raw-SQL indexes (merge_conflicts +
regulatory_decisions unique) as drops — those are false positives
because they were created via `op.execute(...)` outside of model
metadata. Stripped from this migration. Per DEBT D-010 investigation.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '896317a30382'
down_revision: Union[str, Sequence[str], None] = 'adbd97c20143'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'claims',
        'evidence_basis',
        existing_type=sa.VARCHAR(length=128),
        type_=sa.Text(),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'claims',
        'evidence_basis',
        existing_type=sa.Text(),
        type_=sa.VARCHAR(length=128),
        existing_nullable=True,
    )
