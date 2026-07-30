"""add work_tasks, worker_assignments, worker_attendance tables

Revision ID: 007_phase1
Revises: 007_organization_type
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "007_phase1"
down_revision: Union[str, None] = "007_organization_type"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    table_names = inspector.get_table_names()

    if "work_tasks" not in table_names:
        op.create_table(
            "work_tasks",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("cooperative_id", sa.Integer(), sa.ForeignKey("cooperatives.id"), nullable=False, index=True),
            sa.Column("title", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("task_type", sa.String(), nullable=False),
            sa.Column("location", sa.String(), nullable=True),
            sa.Column("scheduled_date", sa.Date(), nullable=False),
            sa.Column("assigned_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("status", sa.String(), server_default="open"),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "worker_assignments" not in table_names:
        op.create_table(
            "worker_assignments",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("work_task_id", sa.Integer(), sa.ForeignKey("work_tasks.id"), nullable=False, index=True),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False, index=True),
            sa.Column("assigned_at", sa.DateTime(), server_default=sa.func.now()),
        )

    if "worker_attendance" not in table_names:
        op.create_table(
            "worker_attendance",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("worker_id", sa.Integer(), sa.ForeignKey("workers.id"), nullable=False, index=True),
            sa.Column("work_task_id", sa.Integer(), sa.ForeignKey("work_tasks.id"), nullable=True, index=True),
            sa.Column("cooperative_id", sa.Integer(), sa.ForeignKey("cooperatives.id"), nullable=False, index=True),
            sa.Column("date", sa.Date(), nullable=False),
            sa.Column("hours_worked", sa.Float(), nullable=True),
            sa.Column("shift", sa.String(), nullable=False),
            sa.Column("logged_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("worker_attendance")
    op.drop_table("worker_assignments")
    op.drop_table("work_tasks")
