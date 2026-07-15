"""Create cooperative administrator audit log."""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "003_admin_audit"
down_revision: Union[str, None] = "002_loan_cancel"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "admin_audit_logs" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("cooperative_id", sa.Integer(), nullable=False),
        sa.Column("actor_id", sa.String(), nullable=False),
        sa.Column("action", sa.String(), nullable=False),
        sa.Column("resource_type", sa.String(), nullable=True),
        sa.Column("resource_id", sa.String(), nullable=True),
        sa.Column("details", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(["cooperative_id"], ["cooperatives.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_admin_audit_logs_id", "admin_audit_logs", ["id"])
    op.create_index("ix_admin_audit_logs_cooperative_id", "admin_audit_logs", ["cooperative_id"])
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"])
    op.create_index("ix_admin_audit_logs_created_at", "admin_audit_logs", ["created_at"])


def downgrade() -> None:
    # Startup metadata may have created this table before Alembic adopted it.
    # Dropping it would risk deleting audit history not owned by this revision.
    pass
