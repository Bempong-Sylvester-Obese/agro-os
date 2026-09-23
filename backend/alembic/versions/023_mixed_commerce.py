"""Animal and mixed lots on intake and aggregation (#249).

``crop_type`` remains the product name (Cocoa, Goats, Milk). New columns
record whether the lot is crop or animal and which unit the quantity uses
so settlement can price heads and litres the same way it prices kilograms.

Revision ID: 023_mixed_commerce
Revises: 022_worker_fields
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

revision: str = "023_mixed_commerce"
down_revision: str | Sequence[str] | None = "022_worker_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLES = ("produce_intakes", "aggregation_batches")


def _has_column(table: str, column: str) -> bool:
    inspector = sa_inspect(op.get_bind())
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    for table in _TABLES:
        if not _has_column(table, "production_kind"):
            op.add_column(
                table,
                sa.Column(
                    "production_kind",
                    sa.String(),
                    nullable=False,
                    server_default="crop",
                ),
            )
        if not _has_column(table, "unit"):
            op.add_column(
                table,
                sa.Column(
                    "unit",
                    sa.String(),
                    nullable=False,
                    server_default="kg",
                ),
            )


def downgrade() -> None:
    for table in _TABLES:
        if _has_column(table, "unit"):
            op.drop_column(table, "unit")
        if _has_column(table, "production_kind"):
            op.drop_column(table, "production_kind")
