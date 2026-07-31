"""Add cooperative market and settlement workflow."""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "009_market_settlement"
down_revision: Union[str, None] = "008_loan_rejection_reasons"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

intake_status = postgresql.ENUM(
    "received",
    "accepted",
    "rejected",
    "batched",
    "cancelled",
    name="intakestatus",
    create_type=False,
)
batch_status = postgresql.ENUM(
    "open",
    "closed",
    "sold",
    name="aggregationbatchstatus",
    create_type=False,
)
sale_status = postgresql.ENUM(
    "draft",
    "confirmed",
    "funded",
    "settled",
    name="producesalestatus",
    create_type=False,
)
receipt_status = postgresql.ENUM(
    "pending",
    "verified",
    "rejected",
    name="receiptstatus",
    create_type=False,
)
settlement_status = postgresql.ENUM(
    "draft",
    "pending_approval",
    "approved",
    "processing",
    "partially_paid",
    "completed",
    name="settlementstatus",
    create_type=False,
)
line_status = postgresql.ENUM(
    "pending",
    "processing",
    "paid",
    "failed",
    name="settlementlinestatus",
    create_type=False,
)
deduction_type = postgresql.ENUM(
    "cooperative_fee",
    "transport",
    "quality",
    "manual",
    "loan",
    name="settlementdeductiontype",
    create_type=False,
)
disbursement_status = postgresql.ENUM(
    "pending",
    "processing",
    "partially_failed",
    "completed",
    name="disbursementbatchstatus",
    create_type=False,
)


def upgrade() -> None:
    bind = op.get_bind()
    commerce_tables = {
        "aggregation_batches",
        "buyers",
        "produce_intakes",
        "produce_sales",
        "buyer_payment_receipts",
        "settlement_runs",
        "settlement_lines",
        "settlement_deductions",
        "disbursement_batches",
    }
    existing_tables = set(sa.inspect(bind).get_table_names())
    adopted_tables = commerce_tables & existing_tables
    if adopted_tables == commerce_tables:
        # Base.metadata.create_all() is used when adopting an existing AgroOS
        # database. In that case the complete target schema already exists.
        return
    if adopted_tables:
        raise RuntimeError(
            "Partial commerce schema detected; restore the pre-migration "
            "database state before retrying revision 009"
        )
    if bind.dialect.name == "postgresql":
        for enum_type in (
            intake_status,
            batch_status,
            sale_status,
            receipt_status,
            settlement_status,
            line_status,
            deduction_type,
            disbursement_status,
        ):
            enum_type.create(bind, checkfirst=True)
        op.execute(
            """
            DO $$
            BEGIN
                IF EXISTS (SELECT 1 FROM pg_type WHERE typname = 'transactiontype') THEN
                    ALTER TYPE transactiontype
                    ADD VALUE IF NOT EXISTS 'settlement_payout';
                END IF;
            END
            $$;
            """
        )
    op.create_table(
        "aggregation_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cooperative_id", sa.Integer(), nullable=False),
        sa.Column("code", sa.String(), nullable=False),
        sa.Column("crop_type", sa.String(), nullable=False),
        sa.Column("status", batch_status, nullable=False, server_default="open"),
        sa.Column(
            "total_quantity_kg",
            sa.Numeric(18, 3),
            nullable=False,
            server_default="0",
        ),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("closed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"]),
        sa.UniqueConstraint(
            "cooperative_id", "code", name="uq_aggregation_batch_code"
        ),
    )
    op.create_index(
        "ix_aggregation_batches_cooperative_id",
        "aggregation_batches",
        ["cooperative_id"],
    )
    op.create_table(
        "buyers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cooperative_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("phone", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"]),
        sa.UniqueConstraint(
            "cooperative_id", "name", name="uq_buyer_cooperative_name"
        ),
    )
    op.create_index("ix_buyers_cooperative_id", "buyers", ["cooperative_id"])
    op.create_table(
        "produce_intakes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cooperative_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("aggregation_batch_id", sa.Integer(), nullable=True),
        sa.Column("crop_type", sa.String(), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(18, 3), nullable=False),
        sa.Column("net_quantity_kg", sa.Numeric(18, 3), nullable=True),
        sa.Column("quality_grade", sa.String(), nullable=True),
        sa.Column("collection_point", sa.String(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("status", intake_status, nullable=False, server_default="received"),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"]),
        sa.ForeignKeyConstraint(
            ["membership_id"], ["cooperative_memberships.id"]
        ),
        sa.ForeignKeyConstraint(
            ["aggregation_batch_id"], ["aggregation_batches.id"]
        ),
    )
    op.create_index(
        "ix_produce_intakes_cooperative_id", "produce_intakes", ["cooperative_id"]
    )
    op.create_index(
        "ix_produce_intakes_membership_id", "produce_intakes", ["membership_id"]
    )
    op.create_index(
        "ix_produce_intakes_aggregation_batch_id",
        "produce_intakes",
        ["aggregation_batch_id"],
    )
    op.create_table(
        "produce_sales",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cooperative_id", sa.Integer(), nullable=False),
        sa.Column("aggregation_batch_id", sa.Integer(), nullable=False),
        sa.Column("buyer_id", sa.Integer(), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("currency", sa.String(), nullable=False, server_default="GHS"),
        sa.Column("status", sale_status, nullable=False, server_default="draft"),
        sa.Column("sold_at", sa.DateTime(), nullable=True),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"]),
        sa.ForeignKeyConstraint(
            ["aggregation_batch_id"], ["aggregation_batches.id"]
        ),
        sa.ForeignKeyConstraint(["buyer_id"], ["buyers.id"]),
        sa.UniqueConstraint(
            "aggregation_batch_id",
            name="uq_produce_sale_aggregation_batch",
        ),
    )
    op.create_index(
        "ix_produce_sales_cooperative_id", "produce_sales", ["cooperative_id"]
    )
    op.create_index(
        "ix_produce_sales_aggregation_batch_id",
        "produce_sales",
        ["aggregation_batch_id"],
    )
    op.create_index("ix_produce_sales_buyer_id", "produce_sales", ["buyer_id"])
    op.create_table(
        "buyer_payment_receipts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cooperative_id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("reference", sa.String(), nullable=False),
        sa.Column("status", receipt_status, nullable=False, server_default="pending"),
        sa.Column("received_at", sa.DateTime(), nullable=False),
        sa.Column("submitted_by", sa.String(), nullable=False),
        sa.Column("verified_by", sa.String(), nullable=True),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["produce_sales.id"]),
        sa.UniqueConstraint(
            "cooperative_id", "reference", name="uq_buyer_receipt_reference"
        ),
    )
    op.create_index(
        "ix_buyer_payment_receipts_cooperative_id",
        "buyer_payment_receipts",
        ["cooperative_id"],
    )
    op.create_index(
        "ix_buyer_payment_receipts_sale_id",
        "buyer_payment_receipts",
        ["sale_id"],
    )
    op.create_table(
        "settlement_runs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("cooperative_id", sa.Integer(), nullable=False),
        sa.Column("sale_id", sa.Integer(), nullable=False),
        sa.Column("status", settlement_status, nullable=False, server_default="draft"),
        sa.Column("currency", sa.String(), nullable=False, server_default="GHS"),
        sa.Column(
            "cooperative_fee_percent",
            sa.Numeric(7, 4),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "transport_total", sa.Numeric(18, 2), nullable=False, server_default="0"
        ),
        sa.Column(
            "quality_total", sa.Numeric(18, 2), nullable=False, server_default="0"
        ),
        sa.Column("gross_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("verified_funds_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("deductions_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("net_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("snapshot_json", sa.Text(), nullable=False),
        sa.Column("calculated_by", sa.String(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.String(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"]),
        sa.ForeignKeyConstraint(["sale_id"], ["produce_sales.id"]),
    )
    op.create_index(
        "ix_settlement_runs_cooperative_id", "settlement_runs", ["cooperative_id"]
    )
    op.create_index("ix_settlement_runs_sale_id", "settlement_runs", ["sale_id"])
    op.create_table(
        "settlement_lines",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_run_id", sa.Integer(), nullable=False),
        sa.Column("membership_id", sa.Integer(), nullable=False),
        sa.Column("quantity_kg", sa.Numeric(18, 3), nullable=False),
        sa.Column("unit_price", sa.Numeric(18, 2), nullable=False),
        sa.Column("gross_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("deductions_total", sa.Numeric(18, 2), nullable=False),
        sa.Column("net_amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("status", line_status, nullable=False, server_default="pending"),
        sa.Column("payout_reference", sa.String(), nullable=False, unique=True),
        sa.Column("paid_at", sa.DateTime(), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(["settlement_run_id"], ["settlement_runs.id"]),
        sa.ForeignKeyConstraint(
            ["membership_id"], ["cooperative_memberships.id"]
        ),
        sa.UniqueConstraint(
            "settlement_run_id", "membership_id", name="uq_settlement_member"
        ),
    )
    op.create_index(
        "ix_settlement_lines_settlement_run_id",
        "settlement_lines",
        ["settlement_run_id"],
    )
    op.create_index(
        "ix_settlement_lines_membership_id", "settlement_lines", ["membership_id"]
    )
    op.create_table(
        "settlement_deductions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_line_id", sa.Integer(), nullable=False),
        sa.Column("deduction_type", deduction_type, nullable=False),
        sa.Column("amount", sa.Numeric(18, 2), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("loan_id", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["settlement_line_id"], ["settlement_lines.id"]),
        sa.ForeignKeyConstraint(["loan_id"], ["loans.id"]),
    )
    op.create_index(
        "ix_settlement_deductions_settlement_line_id",
        "settlement_deductions",
        ["settlement_line_id"],
    )
    op.create_table(
        "disbursement_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settlement_run_id", sa.Integer(), nullable=False),
        sa.Column(
            "status",
            disbursement_status,
            nullable=False,
            server_default="pending",
        ),
        sa.Column("attempt_number", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["settlement_run_id"], ["settlement_runs.id"]),
    )
    op.create_index(
        "ix_disbursement_batches_settlement_run_id",
        "disbursement_batches",
        ["settlement_run_id"],
    )
    op.add_column(
        "transactions",
        sa.Column("settlement_line_id", sa.Integer(), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("disbursement_batch_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_transactions_settlement_line",
        "transactions",
        "settlement_lines",
        ["settlement_line_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_transactions_disbursement_batch",
        "transactions",
        "disbursement_batches",
        ["disbursement_batch_id"],
        ["id"],
    )
    op.create_index(
        "ix_transactions_settlement_line_id",
        "transactions",
        ["settlement_line_id"],
    )
    op.create_index(
        "ix_transactions_disbursement_batch_id",
        "transactions",
        ["disbursement_batch_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_transactions_disbursement_batch_id", table_name="transactions")
    op.drop_index("ix_transactions_settlement_line_id", table_name="transactions")
    op.drop_constraint(
        "fk_transactions_disbursement_batch", "transactions", type_="foreignkey"
    )
    op.drop_constraint(
        "fk_transactions_settlement_line", "transactions", type_="foreignkey"
    )
    op.drop_column("transactions", "disbursement_batch_id")
    op.drop_column("transactions", "settlement_line_id")
    op.drop_table("disbursement_batches")
    op.drop_table("settlement_deductions")
    op.drop_table("settlement_lines")
    op.drop_table("settlement_runs")
    op.drop_table("buyer_payment_receipts")
    op.drop_table("produce_sales")
    op.drop_table("produce_intakes")
    op.drop_table("buyers")
    op.drop_table("aggregation_batches")
