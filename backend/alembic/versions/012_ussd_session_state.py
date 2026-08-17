"""Persist USSD session state.

Revision ID: 012_ussd_session_state
Revises: 011_merge_heads
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "012_ussd_session_state"
down_revision: Union[str, None] = "011_merge_heads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    if "session_state" not in _column_names("ussd_sessions"):
        op.add_column(
            "ussd_sessions",
            sa.Column("session_state", sa.JSON(), nullable=True),
        )


def downgrade() -> None:
    if "session_state" in _column_names("ussd_sessions"):
        op.drop_column("ussd_sessions", "session_state")
