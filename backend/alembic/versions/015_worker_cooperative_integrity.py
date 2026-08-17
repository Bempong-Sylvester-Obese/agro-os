"""Enforce cooperative consistency across worker records.

Revision ID: 015_worker_integrity
Revises: 014_merge_pricing
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op


revision: str = "015_worker_integrity"
down_revision: str | Sequence[str] | None = "014_merge_pricing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


REQUIRED_TABLES = {
    "workers",
    "work_tasks",
    "worker_assignments",
    "worker_attendance",
    "wage_payouts",
}


def _unique_constraint_names(inspector, table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_unique_constraints(table_name)
        if constraint.get("name")
    }


def _foreign_key_names(inspector, table_name: str) -> set[str]:
    return {
        constraint["name"]
        for constraint in inspector.get_foreign_keys(table_name)
        if constraint.get("name")
    }


def _drop_single_foreign_key(
    inspector,
    *,
    table_name: str,
    column_name: str,
    referred_table: str,
) -> None:
    for constraint in inspector.get_foreign_keys(table_name):
        if (
            constraint.get("constrained_columns") == [column_name]
            and constraint.get("referred_table") == referred_table
            and constraint.get("name")
        ):
            op.drop_constraint(
                constraint["name"],
                table_name,
                type_="foreignkey",
            )


def _mismatch_count(bind, sql: str) -> int:
    return int(bind.execute(sa.text(sql)).scalar_one())


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not REQUIRED_TABLES.issubset(inspector.get_table_names()):
        return

    worker_uniques = _unique_constraint_names(inspector, "workers")
    if "uq_workers_cooperative_id_id" not in worker_uniques:
        op.create_unique_constraint(
            "uq_workers_cooperative_id_id",
            "workers",
            ["cooperative_id", "id"],
        )

    task_uniques = _unique_constraint_names(inspector, "work_tasks")
    if "uq_work_tasks_cooperative_id_id" not in task_uniques:
        op.create_unique_constraint(
            "uq_work_tasks_cooperative_id_id",
            "work_tasks",
            ["cooperative_id", "id"],
        )

    assignment_columns = {
        column["name"] for column in inspector.get_columns("worker_assignments")
    }
    if "cooperative_id" not in assignment_columns:
        op.add_column(
            "worker_assignments",
            sa.Column("cooperative_id", sa.Integer(), nullable=True),
        )
        op.create_index(
            "ix_worker_assignments_cooperative_id",
            "worker_assignments",
            ["cooperative_id"],
        )

    mismatch_counts = {
        "worker_assignments": _mismatch_count(
            bind,
            """
            SELECT count(*)
            FROM worker_assignments assignment
            JOIN work_tasks task ON task.id = assignment.work_task_id
            JOIN workers worker ON worker.id = assignment.worker_id
            WHERE task.cooperative_id <> worker.cooperative_id
               OR (
                    assignment.cooperative_id IS NOT NULL
                    AND assignment.cooperative_id <> task.cooperative_id
               )
            """,
        ),
        "worker_attendance": _mismatch_count(
            bind,
            """
            SELECT count(*)
            FROM worker_attendance attendance
            JOIN workers worker ON worker.id = attendance.worker_id
            LEFT JOIN work_tasks task ON task.id = attendance.work_task_id
            WHERE attendance.cooperative_id <> worker.cooperative_id
               OR (
                    attendance.work_task_id IS NOT NULL
                    AND attendance.cooperative_id <> task.cooperative_id
               )
            """,
        ),
        "wage_payouts": _mismatch_count(
            bind,
            """
            SELECT count(*)
            FROM wage_payouts payout
            JOIN workers worker ON worker.id = payout.worker_id
            WHERE payout.cooperative_id <> worker.cooperative_id
            """,
        ),
    }
    invalid = {
        table_name: count
        for table_name, count in mismatch_counts.items()
        if count
    }
    if invalid:
        details = ", ".join(
            f"{table_name}={count}"
            for table_name, count in sorted(invalid.items())
        )
        raise RuntimeError(
            "Cross-cooperative worker records must be corrected before "
            f"migration: {details}"
        )

    bind.execute(
        sa.text(
            """
            UPDATE worker_assignments assignment
            SET cooperative_id = task.cooperative_id
            FROM work_tasks task
            WHERE task.id = assignment.work_task_id
              AND assignment.cooperative_id IS NULL
            """
        )
    )
    op.alter_column(
        "worker_assignments",
        "cooperative_id",
        existing_type=sa.Integer(),
        nullable=False,
    )

    inspector = sa.inspect(bind)
    assignment_fks = _foreign_key_names(inspector, "worker_assignments")
    if "fk_worker_assignments_cooperative_task" not in assignment_fks:
        _drop_single_foreign_key(
            inspector,
            table_name="worker_assignments",
            column_name="work_task_id",
            referred_table="work_tasks",
        )
        op.create_foreign_key(
            "fk_worker_assignments_cooperative_task",
            "worker_assignments",
            "work_tasks",
            ["cooperative_id", "work_task_id"],
            ["cooperative_id", "id"],
            ondelete="CASCADE",
        )
    inspector = sa.inspect(bind)
    assignment_fks = _foreign_key_names(inspector, "worker_assignments")
    if "fk_worker_assignments_cooperative_worker" not in assignment_fks:
        _drop_single_foreign_key(
            inspector,
            table_name="worker_assignments",
            column_name="worker_id",
            referred_table="workers",
        )
        op.create_foreign_key(
            "fk_worker_assignments_cooperative_worker",
            "worker_assignments",
            "workers",
            ["cooperative_id", "worker_id"],
            ["cooperative_id", "id"],
            ondelete="CASCADE",
        )

    inspector = sa.inspect(bind)
    attendance_fks = _foreign_key_names(inspector, "worker_attendance")
    if "fk_worker_attendance_cooperative_worker" not in attendance_fks:
        _drop_single_foreign_key(
            inspector,
            table_name="worker_attendance",
            column_name="worker_id",
            referred_table="workers",
        )
        op.create_foreign_key(
            "fk_worker_attendance_cooperative_worker",
            "worker_attendance",
            "workers",
            ["cooperative_id", "worker_id"],
            ["cooperative_id", "id"],
        )
    inspector = sa.inspect(bind)
    attendance_fks = _foreign_key_names(inspector, "worker_attendance")
    if "fk_worker_attendance_cooperative_task" not in attendance_fks:
        _drop_single_foreign_key(
            inspector,
            table_name="worker_attendance",
            column_name="work_task_id",
            referred_table="work_tasks",
        )
        op.create_foreign_key(
            "fk_worker_attendance_cooperative_task",
            "worker_attendance",
            "work_tasks",
            ["cooperative_id", "work_task_id"],
            ["cooperative_id", "id"],
        )

    inspector = sa.inspect(bind)
    payout_fks = _foreign_key_names(inspector, "wage_payouts")
    if "fk_wage_payouts_cooperative_worker" not in payout_fks:
        _drop_single_foreign_key(
            inspector,
            table_name="wage_payouts",
            column_name="worker_id",
            referred_table="workers",
        )
        op.create_foreign_key(
            "fk_wage_payouts_cooperative_worker",
            "wage_payouts",
            "workers",
            ["cooperative_id", "worker_id"],
            ["cooperative_id", "id"],
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    if not REQUIRED_TABLES.issubset(inspector.get_table_names()):
        return

    constraints = {
        "worker_assignments": _foreign_key_names(
            inspector, "worker_assignments"
        ),
        "worker_attendance": _foreign_key_names(
            inspector, "worker_attendance"
        ),
        "wage_payouts": _foreign_key_names(inspector, "wage_payouts"),
    }
    for table_name, constraint_name in (
        (
            "worker_assignments",
            "fk_worker_assignments_cooperative_task",
        ),
        (
            "worker_assignments",
            "fk_worker_assignments_cooperative_worker",
        ),
        (
            "worker_attendance",
            "fk_worker_attendance_cooperative_worker",
        ),
        (
            "worker_attendance",
            "fk_worker_attendance_cooperative_task",
        ),
        ("wage_payouts", "fk_wage_payouts_cooperative_worker"),
    ):
        if constraint_name in constraints[table_name]:
            op.drop_constraint(
                constraint_name,
                table_name,
                type_="foreignkey",
            )

    op.create_foreign_key(
        "fk_worker_assignments_work_task_id",
        "worker_assignments",
        "work_tasks",
        ["work_task_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_worker_assignments_worker_id",
        "worker_assignments",
        "workers",
        ["worker_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_worker_attendance_worker_id",
        "worker_attendance",
        "workers",
        ["worker_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_worker_attendance_work_task_id",
        "worker_attendance",
        "work_tasks",
        ["work_task_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_wage_payouts_worker_id",
        "wage_payouts",
        "workers",
        ["worker_id"],
        ["id"],
    )

    assignment_indexes = {
        index["name"]
        for index in sa.inspect(bind).get_indexes("worker_assignments")
        if index.get("name")
    }
    if "ix_worker_assignments_cooperative_id" in assignment_indexes:
        op.drop_index(
            "ix_worker_assignments_cooperative_id",
            table_name="worker_assignments",
        )
    op.drop_column("worker_assignments", "cooperative_id")

    inspector = sa.inspect(bind)
    if (
        "uq_work_tasks_cooperative_id_id"
        in _unique_constraint_names(inspector, "work_tasks")
    ):
        op.drop_constraint(
            "uq_work_tasks_cooperative_id_id",
            "work_tasks",
            type_="unique",
        )
    if (
        "uq_workers_cooperative_id_id"
        in _unique_constraint_names(inspector, "workers")
    ):
        op.drop_constraint(
            "uq_workers_cooperative_id_id",
            "workers",
            type_="unique",
        )
