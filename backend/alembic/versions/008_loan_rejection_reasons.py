"""Add durable loan rejection details."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "008_loan_rejection_reasons"
down_revision: Union[str, None] = "007_self_service_reminders"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("loans")}
    if "rejection_reason" not in columns:
        op.add_column("loans", sa.Column("rejection_reason", sa.Text(), nullable=True))
    if "rejected_by" not in columns:
        op.add_column("loans", sa.Column("rejected_by", sa.String(), nullable=True))
    if "rejected_at" not in columns:
        op.add_column("loans", sa.Column("rejected_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    # Preserve decision history in adopted databases.
    pass
