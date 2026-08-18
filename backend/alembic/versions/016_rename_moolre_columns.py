"""Rename moolre_* columns to provider-neutral names.

Revision ID: 016_rename_moolre
Revises: 015_worker_integrity
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "016_rename_moolre"
down_revision: str | Sequence[str] | None = "015_worker_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.alter_column("cooperatives", "moolre_account_number", new_column_name="wallet_account_id")
    op.alter_column("transactions", "moolre_reference", new_column_name="provider_payment_ref")
    op.alter_column("transactions", "moolre_transfer_ref", new_column_name="provider_transfer_ref")
    op.alter_column("loans", "moolre_transfer_ref", new_column_name="provider_transfer_ref")
    op.alter_column("communication_logs", "moolre_ref", new_column_name="provider_ref")
    op.alter_column("payment_webhook_events", "moolre_reference", new_column_name="provider_payment_ref")


def downgrade() -> None:
    op.alter_column("payment_webhook_events", "provider_payment_ref", new_column_name="moolre_reference")
    op.alter_column("communication_logs", "provider_ref", new_column_name="moolre_ref")
    op.alter_column("loans", "provider_transfer_ref", new_column_name="moolre_transfer_ref")
    op.alter_column("transactions", "provider_transfer_ref", new_column_name="moolre_transfer_ref")
    op.alter_column("transactions", "provider_payment_ref", new_column_name="moolre_reference")
    op.alter_column("cooperatives", "wallet_account_id", new_column_name="moolre_account_number")
