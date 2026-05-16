"""phase-1-day8: ADR-0012 ship Deal + drug_deal_link + VIEW update

Revision ID: adbd97c20143
Revises: 84c8d1ea439b
Create Date: 2026-04-19 16:26:09.159904

Promotes Deal from deferred to shipped per ADR-0012. Adds:
  - deals table (BilingualNarrativeMixin shape)
  - drug_deal_link junction
  - entity_relationships VIEW extended to include drug↔deal edges (ADR-0002)

Alembic autogenerate also flagged Day 7's raw-SQL indexes (merge_conflicts,
regulatory_decisions unique) as "to drop" because they aren't in model
metadata. Removed those false positives from this file.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = 'adbd97c20143'
down_revision: Union[str, Sequence[str], None] = '84c8d1ea439b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        'deals',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('deal_type', sa.String(length=32), nullable=False),
        sa.Column('headline', sa.Text(), nullable=False),
        sa.Column('announcement_date', sa.Date(), nullable=True),
        sa.Column('value_usd', sa.BigInteger(), nullable=True),
        sa.Column('acquirer_id', sa.UUID(), nullable=True),
        sa.Column('target_id', sa.UUID(), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('description_zh', sa.Text(), nullable=True),
        sa.Column('description_source_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('strategic_rationale', sa.Text(), nullable=True),
        sa.Column('strategic_rationale_zh', sa.Text(), nullable=True),
        sa.Column('strategic_rationale_source_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('field_provenance', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['acquirer_id'], ['companies.id']),
        sa.ForeignKeyConstraint(['target_id'], ['companies.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_deals_acquirer_id'), 'deals', ['acquirer_id'], unique=False)
    op.create_index(op.f('ix_deals_announcement_date'), 'deals', ['announcement_date'], unique=False)
    op.create_index(op.f('ix_deals_target_id'), 'deals', ['target_id'], unique=False)

    op.create_table(
        'drug_deal_link',
        sa.Column('drug_id', sa.UUID(), nullable=False),
        sa.Column('deal_id', sa.UUID(), nullable=False),
        sa.Column('role', sa.String(length=32), nullable=True),
        sa.ForeignKeyConstraint(['deal_id'], ['deals.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['drug_id'], ['drugs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('drug_id', 'deal_id'),
    )

    # ADR-0002: amend entity_relationships VIEW to include drug↔deal edges.
    # CREATE OR REPLACE is safe — keeps the same view object, reloads body.
    op.execute("DROP VIEW IF EXISTS entity_relationships;")
    op.execute("""
    CREATE VIEW entity_relationships AS
    SELECT 'drug'::text AS source_type, drug_id AS source_id,
           'target'::text AS target_type, target_id AS target_id,
           'hits'::text AS relationship_type
      FROM drug_target_link
    UNION ALL
    SELECT 'target', target_id, 'drug', drug_id, 'hit_by' FROM drug_target_link
    UNION ALL
    SELECT 'drug', drug_id, 'indication', indication_id, 'treats' FROM drug_indication_link
    UNION ALL
    SELECT 'indication', indication_id, 'drug', drug_id, 'treated_by' FROM drug_indication_link
    UNION ALL
    SELECT 'target', target_id, 'indication', indication_id, 'associated_with' FROM target_indication_link
    UNION ALL
    SELECT 'indication', indication_id, 'target', target_id, 'associated_with' FROM target_indication_link
    UNION ALL
    SELECT 'drug', originator_id, 'company', id, 'developed_by' FROM drugs WHERE originator_id IS NOT NULL
    UNION ALL
    SELECT 'company', id, 'drug', originator_id, 'originated' FROM drugs WHERE originator_id IS NOT NULL
    UNION ALL
    SELECT 'clinical_trial', id, 'drug', drug_id, 'tests' FROM clinical_trials WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'drug', drug_id, 'clinical_trial', id, 'tested_in' FROM clinical_trials WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'clinical_trial', id, 'company', sponsor_id, 'sponsored_by' FROM clinical_trials WHERE sponsor_id IS NOT NULL
    UNION ALL
    SELECT 'company', sponsor_id, 'clinical_trial', id, 'sponsors' FROM clinical_trials WHERE sponsor_id IS NOT NULL
    UNION ALL
    SELECT 'regulatory_decision', id, 'drug', drug_id, 'decides_on' FROM regulatory_decisions WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'drug', drug_id, 'regulatory_decision', id, 'has_decision' FROM regulatory_decisions WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'patent', id, 'drug', drug_id, 'protects' FROM patents WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'drug', drug_id, 'patent', id, 'protected_by' FROM patents WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'event', triggered_by, 'event', id, 'triggers' FROM events WHERE triggered_by IS NOT NULL
    UNION ALL
    SELECT 'event', id, 'event', triggered_by, 'triggered_by' FROM events WHERE triggered_by IS NOT NULL
    UNION ALL
    SELECT entity_type, entity_id, 'claim', claim_id, 'has_claim' FROM entity_claim_link
    UNION ALL
    SELECT 'claim', claim_id, entity_type, entity_id, 'about' FROM entity_claim_link
    UNION ALL
    SELECT entity_type, entity_id, 'lesson', lesson_id, 'teaches' FROM entity_lesson_link
    UNION ALL
    SELECT 'lesson', lesson_id, entity_type, entity_id, 'applies_to' FROM entity_lesson_link
    UNION ALL
    SELECT 'event', event_id, entity_type, entity_id, 'involves' FROM event_entity_link
    UNION ALL
    SELECT entity_type, entity_id, 'event', event_id, 'participates_in' FROM event_entity_link
    UNION ALL
    -- ADR-0012: Deal edges
    SELECT 'drug', drug_id, 'deal', deal_id, 'in_deal' FROM drug_deal_link
    UNION ALL
    SELECT 'deal', deal_id, 'drug', drug_id, 'covers_drug' FROM drug_deal_link
    UNION ALL
    SELECT 'company', acquirer_id, 'deal', id, 'acquired_via' FROM deals WHERE acquirer_id IS NOT NULL
    UNION ALL
    SELECT 'deal', id, 'company', acquirer_id, 'acquirer_is' FROM deals WHERE acquirer_id IS NOT NULL
    UNION ALL
    SELECT 'company', target_id, 'deal', id, 'targeted_by' FROM deals WHERE target_id IS NOT NULL
    UNION ALL
    SELECT 'deal', id, 'company', target_id, 'target_is' FROM deals WHERE target_id IS NOT NULL;
    """)


def downgrade() -> None:
    """Downgrade schema."""
    # Revert VIEW to Day-7 shape (without deals edges).
    op.execute("DROP VIEW IF EXISTS entity_relationships;")
    op.execute("""
    CREATE VIEW entity_relationships AS
    SELECT 'drug'::text AS source_type, drug_id AS source_id,
           'target'::text AS target_type, target_id AS target_id,
           'hits'::text AS relationship_type
      FROM drug_target_link
    UNION ALL
    SELECT 'target', target_id, 'drug', drug_id, 'hit_by' FROM drug_target_link
    UNION ALL
    SELECT 'drug', drug_id, 'indication', indication_id, 'treats' FROM drug_indication_link
    UNION ALL
    SELECT 'indication', indication_id, 'drug', drug_id, 'treated_by' FROM drug_indication_link
    UNION ALL
    SELECT 'target', target_id, 'indication', indication_id, 'associated_with' FROM target_indication_link
    UNION ALL
    SELECT 'indication', indication_id, 'target', target_id, 'associated_with' FROM target_indication_link
    UNION ALL
    SELECT 'drug', originator_id, 'company', id, 'developed_by' FROM drugs WHERE originator_id IS NOT NULL
    UNION ALL
    SELECT 'company', id, 'drug', originator_id, 'originated' FROM drugs WHERE originator_id IS NOT NULL
    UNION ALL
    SELECT 'clinical_trial', id, 'drug', drug_id, 'tests' FROM clinical_trials WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'drug', drug_id, 'clinical_trial', id, 'tested_in' FROM clinical_trials WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'clinical_trial', id, 'company', sponsor_id, 'sponsored_by' FROM clinical_trials WHERE sponsor_id IS NOT NULL
    UNION ALL
    SELECT 'company', sponsor_id, 'clinical_trial', id, 'sponsors' FROM clinical_trials WHERE sponsor_id IS NOT NULL
    UNION ALL
    SELECT 'regulatory_decision', id, 'drug', drug_id, 'decides_on' FROM regulatory_decisions WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'drug', drug_id, 'regulatory_decision', id, 'has_decision' FROM regulatory_decisions WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'patent', id, 'drug', drug_id, 'protects' FROM patents WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'drug', drug_id, 'patent', id, 'protected_by' FROM patents WHERE drug_id IS NOT NULL
    UNION ALL
    SELECT 'event', triggered_by, 'event', id, 'triggers' FROM events WHERE triggered_by IS NOT NULL
    UNION ALL
    SELECT 'event', id, 'event', triggered_by, 'triggered_by' FROM events WHERE triggered_by IS NOT NULL
    UNION ALL
    SELECT entity_type, entity_id, 'claim', claim_id, 'has_claim' FROM entity_claim_link
    UNION ALL
    SELECT 'claim', claim_id, entity_type, entity_id, 'about' FROM entity_claim_link
    UNION ALL
    SELECT entity_type, entity_id, 'lesson', lesson_id, 'teaches' FROM entity_lesson_link
    UNION ALL
    SELECT 'lesson', lesson_id, entity_type, entity_id, 'applies_to' FROM entity_lesson_link
    UNION ALL
    SELECT 'event', event_id, entity_type, entity_id, 'involves' FROM event_entity_link
    UNION ALL
    SELECT entity_type, entity_id, 'event', event_id, 'participates_in' FROM event_entity_link;
    """)

    op.drop_table('drug_deal_link')
    op.drop_index(op.f('ix_deals_target_id'), table_name='deals')
    op.drop_index(op.f('ix_deals_announcement_date'), table_name='deals')
    op.drop_index(op.f('ix_deals_acquirer_id'), table_name='deals')
    op.drop_table('deals')
