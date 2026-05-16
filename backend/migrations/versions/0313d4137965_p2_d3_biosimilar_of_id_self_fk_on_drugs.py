"""p2-d3: biosimilar_of_id self-FK on drugs

Revision ID: 0313d4137965
Revises: 896317a30382
Create Date: 2026-04-19 20:38:40.427329

Adds Drug.biosimilar_of_id self-reference per §14.2. A biosimilar Drug
row points at its reference biologic; reverse relationship Drug.biosimilars
surfaces the list for Humira's `biosimilars_exist` test.

Autogen wanted to drop uq_regulatory_decisions_app_sub (Day 7 raw-SQL
index not in model metadata) — stripped as false positive per DEBT D-010.
FK constraint is explicitly named so downgrade can drop it.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = '0313d4137965'
down_revision: Union[str, Sequence[str], None] = '896317a30382'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column('drugs', sa.Column('biosimilar_of_id', sa.UUID(), nullable=True))
    op.create_index(op.f('ix_drugs_biosimilar_of_id'), 'drugs', ['biosimilar_of_id'], unique=False)
    op.create_foreign_key(
        'fk_drugs_biosimilar_of_id',
        'drugs', 'drugs',
        ['biosimilar_of_id'], ['id'],
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('fk_drugs_biosimilar_of_id', 'drugs', type_='foreignkey')
    op.drop_index(op.f('ix_drugs_biosimilar_of_id'), table_name='drugs')
    op.drop_column('drugs', 'biosimilar_of_id')
