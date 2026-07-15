"""Add cooperative user activation state."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "004_user_active"
down_revision: Union[str, None] = "003_admin_audit"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    columns = {column["name"] for column in sa.inspect(op.get_bind()).get_columns("users")}
    if "is_active" in columns:
        return
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
    )


def downgrade() -> None:
    # This column may have been adopted from startup metadata; retain it rather
    # than risk removing schema and data not created by this revision.
    pass
