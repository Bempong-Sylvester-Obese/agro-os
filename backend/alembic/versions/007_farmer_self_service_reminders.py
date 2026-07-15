"""Add durable loan repayment reminder deliveries."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "007_self_service_reminders"
down_revision: Union[str, None] = "006_farmer_finance_flows"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if "loan_reminders" in inspector.get_table_names():
        return
    op.create_table(
        "loan_reminders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("loan_id", sa.Integer(), sa.ForeignKey("loans.id"), nullable=False),
        sa.Column("reminder_kind", sa.String(), nullable=False),
        sa.Column("scheduled_for", sa.Date(), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("provider_reference", sa.String(), nullable=True),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("manual", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint(
            "loan_id",
            "reminder_kind",
            "scheduled_for",
            name="uq_loan_reminder_delivery",
        ),
    )
    op.create_index("ix_loan_reminders_id", "loan_reminders", ["id"])
    op.create_index("ix_loan_reminders_loan_id", "loan_reminders", ["loan_id"])


def downgrade() -> None:
    # Preserve reminder delivery history in adopted databases.
    pass
