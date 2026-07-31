"""add_subscription_tracking

Revision ID: fbe32acc0767
Revises: 010_unified_production
Create Date: 2026-07-18 22:26:23.385535

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "fbe32acc0767"
down_revision: Union[str, None] = "010_unified_production"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    cooperative_columns = _column_names("cooperatives")
    if "subscription_status" not in cooperative_columns:
        op.add_column(
            "cooperatives",
            sa.Column(
                "subscription_status",
                sa.String(),
                nullable=False,
                server_default="active",
            ),
        )
    if "subscription_expires_at" not in cooperative_columns:
        op.add_column(
            "cooperatives",
            sa.Column("subscription_expires_at", sa.DateTime(), nullable=True),
        )


def downgrade() -> None:
    cooperative_columns = _column_names("cooperatives")
    if "subscription_expires_at" in cooperative_columns:
        op.drop_column("cooperatives", "subscription_expires_at")
    if "subscription_status" in cooperative_columns:
        op.drop_column("cooperatives", "subscription_status")
