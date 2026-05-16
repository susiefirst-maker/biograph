"""p7-d19: retire D-004 — lowercase enum values for StrEnum columns

Revision ID: a7b9f4e2d501
Revises: 0313d4137965
Create Date: 2026-04-19 23:00:00.000000

Retires DEBT D-004. The three PG enum types (patent_source_register,
claim_type_kind, lesson_type_kind) were created with member NAMES
(uppercase, e.g. 'ORANGE_BOOK') while the Python StrEnum `.value` is
lowercase ('orange_book'). Raw SQL `WHERE claim_type = 'verified_fact'`
currently misses all rows.

`ALTER TYPE ... RENAME VALUE` (Postgres 10+) is atomic and safe for
the small number of rows we have. Models get `values_callable=...`
in a separate change so future inserts use the canonical lowercase.
"""

from typing import Sequence, Union

from alembic import op


revision: str = 'a7b9f4e2d501'
down_revision: Union[str, Sequence[str], None] = '0313d4137965'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


_RENAMES = [
    ("patent_source_register", [
        ("ORANGE_BOOK", "orange_book"),
        ("PURPLE_BOOK", "purple_book"),
        ("USPTO_MANUAL", "uspto_manual"),
        ("LITIGATION", "litigation"),
        ("ARTICLE_CITATION", "article_citation"),
    ]),
    ("claim_type_kind", [
        ("VERIFIED_FACT", "verified_fact"),
        ("ATTRIBUTED_ANALYSIS", "attributed_analysis"),
        ("PREDICTION", "prediction"),
        ("OPINION", "opinion"),
        ("DISPUTED", "disputed"),
    ]),
    ("lesson_type_kind", [
        ("STRATEGIC_COMMERCIAL", "strategic_commercial"),
        ("SCIENTIFIC_MECHANISTIC", "scientific_mechanistic"),
        ("REGULATORY_PATHWAY", "regulatory_pathway"),
        ("COMPETITIVE_DYNAMICS", "competitive_dynamics"),
        ("CLINICAL_DEVELOPMENT", "clinical_development"),
        ("MANUFACTURING_CMC", "manufacturing_cmc"),
        ("MARKET_ACCESS_PRICING", "market_access_pricing"),
    ]),
]


def upgrade() -> None:
    for type_name, renames in _RENAMES:
        for old, new in renames:
            op.execute(
                f"ALTER TYPE {type_name} RENAME VALUE '{old}' TO '{new}';"
            )


def downgrade() -> None:
    for type_name, renames in _RENAMES:
        for old, new in renames:
            op.execute(
                f"ALTER TYPE {type_name} RENAME VALUE '{new}' TO '{old}';"
            )
