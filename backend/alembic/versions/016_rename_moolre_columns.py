"""Rename moolre_* columns to provider-neutral names.

Revision ID: 016_rename_moolre
Revises: 015_worker_integrity
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

revision: str = "016_rename_moolre"
down_revision: str | Sequence[str] | None = "015_worker_integrity"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_RENAMES = [
    ("cooperatives", "moolre_account_number", "wallet_account_id"),
    ("transactions", "moolre_reference", "provider_payment_ref"),
    ("transactions", "moolre_transfer_ref", "provider_transfer_ref"),
    ("loans", "moolre_transfer_ref", "provider_transfer_ref"),
    ("communication_logs", "moolre_ref", "provider_ref"),
    ("payment_webhook_events", "moolre_reference", "provider_payment_ref"),
]


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    cols = {c["name"] for c in sa_inspect(bind).get_columns(table)}
    return column in cols


def upgrade() -> None:
    for table, old_name, new_name in _RENAMES:
        if _column_exists(table, old_name):
            op.alter_column(table, old_name, new_column_name=new_name)


def downgrade() -> None:
    for table, old_name, new_name in reversed(_RENAMES):
        if _column_exists(table, new_name):
            op.alter_column(table, new_name, new_column_name=old_name)
