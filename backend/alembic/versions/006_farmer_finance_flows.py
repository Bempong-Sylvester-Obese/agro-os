"""Persist farmer-originated loan and customer payment handoff state."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "006_farmer_finance_flows"
down_revision: Union[str, None] = "005_review_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    loan_columns = {column["name"] for column in inspector.get_columns("loans")}
    if "request_channel" not in loan_columns:
        op.add_column(
            "loans",
            sa.Column(
                "request_channel",
                sa.String(),
                nullable=False,
                server_default="legacy",
            ),
        )

    transaction_columns = {
        column["name"] for column in inspector.get_columns("transactions")
    }
    if "initiation_channel" not in transaction_columns:
        op.add_column(
            "transactions",
            sa.Column(
                "initiation_channel",
                sa.String(),
                nullable=False,
                server_default="legacy",
            ),
        )
    if "customer_action" not in transaction_columns:
        op.add_column(
            "transactions",
            sa.Column(
                "customer_action",
                sa.String(),
                nullable=False,
                server_default="none",
            ),
        )
    if "action_expires_at" not in transaction_columns:
        op.add_column(
            "transactions",
            sa.Column("action_expires_at", sa.DateTime(), nullable=True),
        )
    if "loan_id" not in transaction_columns:
        op.add_column(
            "transactions",
            sa.Column(
                "loan_id",
                sa.Integer(),
                sa.ForeignKey("loans.id"),
                nullable=True,
            ),
        )

    inspector = sa.inspect(bind)
    transaction_indexes = {
        index["name"] for index in inspector.get_indexes("transactions")
    }
    if "ix_transactions_customer_action" not in transaction_indexes:
        op.create_index(
            "ix_transactions_customer_action",
            "transactions",
            ["customer_action"],
        )
    if "ix_transactions_pending_customer_action" not in transaction_indexes:
        op.create_index(
            "ix_transactions_pending_customer_action",
            "transactions",
            ["membership_id", "status", "customer_action"],
        )
    if "ix_transactions_loan_id" not in transaction_indexes:
        op.create_index(
            "ix_transactions_loan_id",
            "transactions",
            ["loan_id"],
        )


def downgrade() -> None:
    # Preserve provenance and payment handoff history in adopted databases.
    pass
