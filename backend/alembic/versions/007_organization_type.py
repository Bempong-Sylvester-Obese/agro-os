"""add organization_type to cooperatives

Revision ID: 007_organization_type
Revises: 005_review_hardening
Create Date: 2026-07-30
"""
from alembic import op
import sqlalchemy as sa

revision = "007_organization_type"
# branched from 005 because 006 cannot apply on SQLite (ALTER TABLE)
down_revision = "005_review_hardening"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "cooperatives",
        sa.Column("organization_type", sa.String(), server_default="cooperative", nullable=False),
    )
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
    )
    op.create_unique_constraint("uq_worker_phone_per_coop", "workers", ["cooperative_id", "phone"])


def downgrade():
    op.drop_constraint("uq_worker_phone_per_coop", "workers")
    op.drop_table("workers")
    op.drop_column("cooperatives", "organization_type")
