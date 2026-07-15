"""Add safe loan cancellation metadata."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "002_loan_cancel"
down_revision: Union[str, None] = "001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE loanstatus ADD VALUE IF NOT EXISTS 'cancelled'")
    columns = {column["name"] for column in sa.inspect(bind).get_columns("loans")}
    if "cancelled_by" not in columns:
        op.add_column("loans", sa.Column("cancelled_by", sa.String(), nullable=True))
    if "cancelled_at" not in columns:
        op.add_column("loans", sa.Column("cancelled_at", sa.DateTime(), nullable=True))
    if "cancellation_reason" not in columns:
        op.add_column("loans", sa.Column("cancellation_reason", sa.Text(), nullable=True))


def downgrade() -> None:
    # This adoption migration may have skipped pre-existing columns created by
    # startup metadata. Their ownership cannot be reconstructed safely, and the
    # PostgreSQL enum value is irreversible, so downgrade is intentionally a no-op.
    pass
