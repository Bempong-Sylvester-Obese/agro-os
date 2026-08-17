"""Add monthly SMS entitlement counters.

Revision ID: 012_billing_entitlements
Revises: 011_merge_heads
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "012_billing_entitlements"
down_revision: str | None = "011_merge_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_names(table_name: str) -> set[str]:
    inspector = sa.inspect(op.get_bind())
    if table_name not in inspector.get_table_names():
        return set()
    return {column["name"] for column in inspector.get_columns(table_name)}


def upgrade() -> None:
    cooperative_columns = _column_names("cooperatives")
    if not cooperative_columns:
        return
    if "sms_sent_this_month" not in cooperative_columns:
        op.add_column(
            "cooperatives",
            sa.Column(
                "sms_sent_this_month",
                sa.Integer(),
                nullable=False,
                server_default="0",
            ),
        )
    if "sms_month_reset" not in cooperative_columns:
        op.add_column(
            "cooperatives",
            sa.Column("sms_month_reset", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    cooperative_columns = _column_names("cooperatives")
    if "sms_month_reset" in cooperative_columns:
        op.drop_column("cooperatives", "sms_month_reset")
    if "sms_sent_this_month" in cooperative_columns:
        op.drop_column("cooperatives", "sms_sent_this_month")
