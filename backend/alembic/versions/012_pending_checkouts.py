"""pending_checkouts

Revision ID: 012_pending_checkouts
Revises: 011_merge_heads
Create Date: 2026-08-12 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "012_pending_checkouts"
down_revision: Union[str, None] = "011_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if "pending_checkouts" not in inspector.get_table_names():
        op.create_table(
            "pending_checkouts",
            sa.Column("id", sa.Integer(), primary_key=True, index=True),
            sa.Column("reference", sa.String(), nullable=False, unique=True, index=True),
            sa.Column("plan_key", sa.String(), nullable=False),
            sa.Column("band", sa.String(), nullable=True),
            sa.Column("amount", sa.Float(), nullable=False),
            sa.Column("currency", sa.String(), default="GHS"),
            sa.Column("organisation", sa.String(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("member_count", sa.Integer(), nullable=True),
            sa.Column("role", sa.String(), nullable=True),
            sa.Column("organization_type", sa.String(), default="cooperative", nullable=False),
            sa.Column("status", sa.String(), default="pending", nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        )
    cooperative_columns = _column_names("cooperatives")
    if "subscription_band" not in cooperative_columns:
        op.add_column("cooperatives", sa.Column("subscription_band", sa.String(), nullable=True))


def downgrade() -> None:
    cooperative_columns = _column_names("cooperatives")
    if "subscription_band" in cooperative_columns:
        op.drop_column("cooperatives", "subscription_band")
    op.drop_table("pending_checkouts")
