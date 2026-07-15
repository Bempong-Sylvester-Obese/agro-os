"""Harden review-sensitive audit, onboarding, and confirmation schema."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "005_review_hardening"
down_revision: Union[str, None] = "004_user_active"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    audit_columns = {
        column["name"]: column for column in inspector.get_columns("admin_audit_logs")
    }
    created_at = audit_columns["created_at"]
    if created_at.get("nullable", True) or created_at.get("default") is None:
        op.execute(
            sa.text(
                "UPDATE admin_audit_logs "
                "SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"
            )
        )
        if bind.dialect.name == "sqlite":
            with op.batch_alter_table("admin_audit_logs") as batch:
                batch.alter_column(
                    "created_at",
                    existing_type=sa.DateTime(),
                    nullable=False,
                    server_default=sa.func.now(),
                )
        else:
            op.alter_column(
                "admin_audit_logs",
                "created_at",
                existing_type=sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            )

    cooperative_columns = {
        column["name"] for column in inspector.get_columns("cooperatives")
    }
    if "subscription_plan" not in cooperative_columns:
        op.add_column(
            "cooperatives",
            sa.Column(
                "subscription_plan",
                sa.String(),
                nullable=False,
                server_default="starter",
            ),
        )

    user_columns = {column["name"] for column in inspector.get_columns("users")}
    if "onboarding_role" not in user_columns:
        op.add_column(
            "users",
            sa.Column("onboarding_role", sa.String(), nullable=True),
        )

    if "admin_action_confirmations" not in tables:
        op.create_table(
            "admin_action_confirmations",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("token_id", sa.String(), nullable=False, unique=True),
            sa.Column("cooperative_id", sa.Integer(), nullable=False),
            sa.Column("user_id", sa.Integer(), nullable=False),
            sa.Column("action", sa.String(), nullable=False),
            sa.Column("expires_at", sa.DateTime(), nullable=False),
            sa.Column("used_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"]),
            sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        )
        op.create_index(
            "ix_admin_action_confirmations_token_id",
            "admin_action_confirmations",
            ["token_id"],
            unique=True,
        )
        op.create_index(
            "ix_admin_action_confirmations_cooperative_id",
            "admin_action_confirmations",
            ["cooperative_id"],
        )
        op.create_index(
            "ix_admin_action_confirmations_user_id",
            "admin_action_confirmations",
            ["user_id"],
        )

    if "demo_bookings" not in tables:
        op.create_table(
            "demo_bookings",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("reference", sa.String(), nullable=False, unique=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("email", sa.String(), nullable=False),
            sa.Column("phone", sa.String(), nullable=True),
            sa.Column("cooperative", sa.String(), nullable=False),
            sa.Column("size", sa.String(), nullable=False),
            sa.Column("topic", sa.String(), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("selected_date", sa.Date(), nullable=False),
            sa.Column("selected_time", sa.String(), nullable=False),
            sa.Column(
                "is_enterprise", sa.Boolean(), nullable=False, server_default=sa.false()
            ),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
        )
        op.create_index(
            "ix_demo_bookings_reference",
            "demo_bookings",
            ["reference"],
            unique=True,
        )
        op.create_index("ix_demo_bookings_email", "demo_bookings", ["email"])
        op.create_index(
            "ix_demo_bookings_selected_date",
            "demo_bookings",
            ["selected_date"],
        )


def downgrade() -> None:
    # Startup metadata may pre-create every object in this adoption migration.
    # Preserve data rather than attempting a destructive ownership guess.
    pass
