"""Rotating refresh tokens for staff sessions (#248).

Access tokens are now short-lived (60 minutes in production). Instead of a
7-day bearer token, the dashboard holds an opaque refresh token that is
exchanged — and rotated — at ``POST /auth/refresh``. Only the SHA-256 hash
of each refresh token is stored; a password change or reset revokes every
live token for the user.

Revision ID: 021_staff_refresh_tokens
Revises: 020_membership_consent_audit
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

revision: str = "021_staff_refresh_tokens"
down_revision: str | Sequence[str] | None = "020_membership_consent_audit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "staff_refresh_tokens"


def upgrade() -> None:
    if _TABLE in sa_inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("revoked_at", sa.DateTime(), nullable=True),
        sa.Column("rotated", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.create_index(f"ix_{_TABLE}_user_id", _TABLE, ["user_id"])
    op.create_index(f"ix_{_TABLE}_token_hash", _TABLE, ["token_hash"], unique=True)


def downgrade() -> None:
    if _TABLE not in sa_inspect(op.get_bind()).get_table_names():
        return
    op.drop_index(f"ix_{_TABLE}_token_hash", table_name=_TABLE)
    op.drop_index(f"ix_{_TABLE}_user_id", table_name=_TABLE)
    op.drop_table(_TABLE)
