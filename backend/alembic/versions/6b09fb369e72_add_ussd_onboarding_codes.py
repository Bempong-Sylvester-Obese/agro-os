"""Add USSD onboarding codes

Revision ID: 6b09fb369e72
Revises: 4f1af1158aec
Create Date: 2026-07-18 23:40:29.817035

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "6b09fb369e72"
down_revision: Union[str, None] = "4f1af1158aec"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def _index_names(table_name: str) -> set[str]:
    return {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes(table_name)
        if index.get("name")
    }


def upgrade() -> None:
    membership_columns = _column_names("cooperative_memberships")
    membership_indexes = _index_names("cooperative_memberships")
    if "farmer_code" not in membership_columns:
        op.add_column(
            "cooperative_memberships",
            sa.Column("farmer_code", sa.String(length=6), nullable=True),
        )
    if "ix_cooperative_memberships_farmer_code" not in membership_indexes:
        op.create_index(
            op.f("ix_cooperative_memberships_farmer_code"),
            "cooperative_memberships",
            ["farmer_code"],
            unique=False,
        )

    cooperative_columns = _column_names("cooperatives")
    cooperative_indexes = _index_names("cooperatives")
    if "ussd_code" not in cooperative_columns:
        op.add_column(
            "cooperatives",
            sa.Column("ussd_code", sa.String(length=4), nullable=True),
        )
    if "ix_cooperatives_ussd_code" not in cooperative_indexes:
        op.create_index(
            op.f("ix_cooperatives_ussd_code"),
            "cooperatives",
            ["ussd_code"],
            unique=True,
        )


def downgrade() -> None:
    cooperative_indexes = _index_names("cooperatives")
    cooperative_columns = _column_names("cooperatives")
    if "ix_cooperatives_ussd_code" in cooperative_indexes:
        op.drop_index(op.f("ix_cooperatives_ussd_code"), table_name="cooperatives")
    if "ussd_code" in cooperative_columns:
        op.drop_column("cooperatives", "ussd_code")

    membership_indexes = _index_names("cooperative_memberships")
    membership_columns = _column_names("cooperative_memberships")
    if "ix_cooperative_memberships_farmer_code" in membership_indexes:
        op.drop_index(
            op.f("ix_cooperative_memberships_farmer_code"),
            table_name="cooperative_memberships",
        )
    if "farmer_code" in membership_columns:
        op.drop_column("cooperative_memberships", "farmer_code")
