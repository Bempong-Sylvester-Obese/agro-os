"""Hire date, pay type, and optional user link on workers (#254).

Solo-farm labor records need a hire date, how the wage is priced
(daily / shift / monthly), and an optional dashboard ``user_id`` so a
supervisor login can be tied to a worker row. Workers remain a distinct
table from memberships; this migration only adds columns.

Revision ID: 022_worker_fields
Revises: 021_staff_refresh_tokens
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

revision: str = "022_worker_fields"
down_revision: str | Sequence[str] | None = "021_staff_refresh_tokens"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "workers"


def _has_column(column: str) -> bool:
    inspector = sa_inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    if not _has_column("hire_date"):
        op.add_column(_TABLE, sa.Column("hire_date", sa.Date(), nullable=True))
    if not _has_column("pay_type"):
        op.add_column(
            _TABLE,
            sa.Column(
                "pay_type",
                sa.String(),
                nullable=False,
                server_default="daily",
            ),
        )
    if not _has_column("user_id"):
        op.add_column(
            _TABLE,
            sa.Column(
                "user_id",
                sa.Integer(),
                sa.ForeignKey("users.id", ondelete="SET NULL"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    if _has_column("user_id"):
        op.drop_column(_TABLE, "user_id")
    if _has_column("pay_type"):
        op.drop_column(_TABLE, "pay_type")
    if _has_column("hire_date"):
        op.drop_column(_TABLE, "hire_date")
