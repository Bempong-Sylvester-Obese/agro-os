"""Rename wage_payouts.moolre_reference to provider_payment_ref.

Revision ID: 017_wage_payout_ref
Revises: 016_rename_moolre
"""

from collections.abc import Sequence

from sqlalchemy import inspect as sa_inspect

from alembic import op

revision: str = "017_wage_payout_ref"
down_revision: str | Sequence[str] | None = "016_rename_moolre"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "wage_payouts"
_OLD = "moolre_reference"
_NEW = "provider_payment_ref"


def _column_exists(table: str, column: str) -> bool:
    bind = op.get_bind()
    inspector = sa_inspect(bind)
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    if _column_exists(_TABLE, _OLD) and not _column_exists(_TABLE, _NEW):
        op.alter_column(_TABLE, _OLD, new_column_name=_NEW)


def downgrade() -> None:
    if _column_exists(_TABLE, _NEW) and not _column_exists(_TABLE, _OLD):
        op.alter_column(_TABLE, _NEW, new_column_name=_OLD)
