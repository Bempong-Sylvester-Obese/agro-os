"""Add cooperative completeness auth, consent, and announcements fields.

Revision ID: 012_coop_complete
Revises: 011_merge_heads
Create Date: 2026-08-17
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "012_coop_complete"
down_revision: str | None = "011_merge_heads"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    user_columns = _column_names("users")
    for column in (
        sa.Column("reset_token", sa.String(), nullable=True),
        sa.Column("reset_token_expires_at", sa.DateTime(), nullable=True),
        sa.Column("invite_token", sa.String(), nullable=True),
        sa.Column("invite_token_expires_at", sa.DateTime(), nullable=True),
    ):
        if column.name not in user_columns:
            op.add_column("users", column)
    if "must_change_password" not in user_columns:
        op.add_column(
            "users",
            sa.Column(
                "must_change_password",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )

    membership_columns = _column_names("cooperative_memberships")
    if "sms_consent" not in membership_columns:
        op.add_column(
            "cooperative_memberships",
            sa.Column(
                "sms_consent",
                sa.Boolean(),
                nullable=False,
                server_default=sa.true(),
            ),
        )

    if not sa.inspect(op.get_bind()).has_table("announcements"):
        op.create_table(
            "announcements",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("cooperative_id", sa.Integer(), nullable=False),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("body", sa.Text(), nullable=False),
            sa.Column(
                "send_sms",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
            sa.Column("created_by", sa.Integer(), nullable=True),
            sa.Column("deleted_at", sa.DateTime(), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"]),
            sa.ForeignKeyConstraint(["created_by"], ["users.id"]),
            sa.PrimaryKeyConstraint("id"),
        )
        op.create_index(
            op.f("ix_announcements_cooperative_id"),
            "announcements",
            ["cooperative_id"],
            unique=False,
        )


def downgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    if inspector.has_table("announcements"):
        announcement_indexes = {
            index["name"]
            for index in inspector.get_indexes("announcements")
            if index.get("name")
        }
        if "ix_announcements_cooperative_id" in announcement_indexes:
            op.drop_index(
                op.f("ix_announcements_cooperative_id"),
                table_name="announcements",
            )
        op.drop_table("announcements")

    membership_columns = _column_names("cooperative_memberships")
    if "sms_consent" in membership_columns:
        op.drop_column("cooperative_memberships", "sms_consent")

    user_columns = _column_names("users")
    for column_name in (
        "must_change_password",
        "invite_token_expires_at",
        "invite_token",
        "reset_token_expires_at",
        "reset_token",
    ):
        if column_name in user_columns:
            op.drop_column("users", column_name)
