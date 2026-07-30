"""add organization_type to cooperatives and create workers table

Revision ID: 007_organization_type
Revises: 006_farmer_finance_flows
Create Date: 2026-07-30
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_organization_type"
down_revision: Union[str, None] = "006_farmer_finance_flows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    coop_columns = {col["name"] for col in inspector.get_columns("cooperatives")}

    if "organization_type" not in coop_columns:
        op.add_column(
            "cooperatives",
            sa.Column("organization_type", sa.String(), server_default="cooperative", nullable=False),
        )

    table_names = inspector.get_table_names()
    if "workers" not in table_names:
        op.create_table(
            "workers",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cooperative_id", sa.Integer(), sa.ForeignKey("cooperatives.id"), nullable=False, index=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("phone", sa.String(), nullable=False, index=True),
            sa.Column("wage_rate", sa.Float(), server_default="0.0"),
            sa.Column("role", sa.String(), server_default="worker"),
            sa.Column("status", sa.String(), server_default="active"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
            sa.UniqueConstraint("cooperative_id", "phone", name="uq_worker_phone_per_coop"),
        )


def downgrade() -> None:
    try:
        op.drop_constraint("uq_worker_phone_per_coop", "workers")
    except NotImplementedError:
        pass
    op.drop_table("workers")
    op.drop_column("cooperatives", "organization_type")
