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
    inspector = sa.inspect(bind)
    if "loans" not in inspector.get_table_names():
        return
    if bind.dialect.name == "postgresql":
        enum_type = bind.execute(
            sa.text(
                """
                SELECT type_ns.nspname, type_def.typname
                FROM pg_attribute attribute
                JOIN pg_type type_def ON type_def.oid = attribute.atttypid
                JOIN pg_namespace type_ns ON type_ns.oid = type_def.typnamespace
                WHERE attribute.attrelid = to_regclass('loans')
                  AND attribute.attname = 'status'
                  AND NOT attribute.attisdropped
                  AND type_def.typtype = 'e'
                """
            )
        ).first()
        if enum_type:
            preparer = bind.dialect.identifier_preparer
            enum_schema, enum_name = enum_type
            qualified_type = (
                f"{preparer.quote(enum_schema)}.{preparer.quote(enum_name)}"
            )
            op.execute(
                f"ALTER TYPE {qualified_type} "
                "ADD VALUE IF NOT EXISTS 'cancelled'"
            )
    columns = {column["name"] for column in inspector.get_columns("loans")}
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
