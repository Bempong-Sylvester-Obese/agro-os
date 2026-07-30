"""add organization_type to cooperatives

Revision ID: 007_organization_type
Revises: 006_farmer_finance_flows
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "007_organization_type"
down_revision = "005_review_hardening"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cooperatives",
        sa.Column("organization_type", sa.String(), server_default="cooperative", nullable=False),
    )


def downgrade():
    op.drop_column("cooperatives", "organization_type")
