"""add_membership_id

Revision ID: 4f1af1158aec
Revises: fbe32acc0767
Create Date: 2026-07-18 22:39:44.626410

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "4f1af1158aec"
down_revision: Union[str, None] = "fbe32acc0767"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {
        column["name"]: column
        for column in sa.inspect(op.get_bind()).get_columns("cooperative_memberships")
    }
    membership_status = columns.get("membership_status")
    if membership_status is not None and membership_status.get("nullable") is False:
        op.alter_column(
            "cooperative_memberships",
            "membership_status",
            existing_type=postgresql.ENUM(
                "active", "inactive", "suspended", name="membershipstatus"
            ),
            nullable=True,
            existing_server_default=sa.text("'active'::membershipstatus"),
        )


def downgrade() -> None:
    columns = {
        column["name"]: column
        for column in sa.inspect(op.get_bind()).get_columns("cooperative_memberships")
    }
    membership_status = columns.get("membership_status")
    if membership_status is not None and membership_status.get("nullable") is True:
        op.alter_column(
            "cooperative_memberships",
            "membership_status",
            existing_type=postgresql.ENUM(
                "active", "inactive", "suspended", name="membershipstatus"
            ),
            nullable=False,
            existing_server_default=sa.text("'active'::membershipstatus"),
        )
