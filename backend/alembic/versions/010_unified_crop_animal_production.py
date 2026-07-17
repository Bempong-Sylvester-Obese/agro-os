"""Add unified crop and animal production fields."""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "010_unified_production"
down_revision: Union[str, None] = "009_market_settlement"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _column_names(table_name: str) -> set[str]:
    return {
        column["name"]
        for column in sa.inspect(op.get_bind()).get_columns(table_name)
    }


def upgrade() -> None:
    membership_columns = _column_names("cooperative_memberships")
    for column in (
        sa.Column(
            "production_focus",
            sa.String(),
            nullable=True,
            server_default="crop",
        ),
        sa.Column("animal_type", sa.String(), nullable=True),
        sa.Column("animal_scale", sa.Float(), nullable=True),
    ):
        if column.name not in membership_columns:
            op.add_column("cooperative_memberships", column)

    production_columns = _column_names("productions")
    for column in (
        sa.Column(
            "production_kind",
            sa.String(),
            nullable=True,
            server_default="crop",
        ),
        sa.Column("product_name", sa.String(), nullable=True),
        sa.Column("activity", sa.String(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True, server_default="kg"),
        sa.Column("expected_quantity", sa.Float(), nullable=True),
        sa.Column("quantity", sa.Float(), nullable=True),
        sa.Column("production_date", sa.DateTime(), nullable=True),
    ):
        if column.name not in production_columns:
            op.add_column("productions", column)

    op.execute(
        """
        UPDATE cooperative_memberships
        SET production_focus = 'crop'
        WHERE production_focus IS NULL
        """
    )
    op.execute(
        """
        UPDATE productions
        SET production_kind = COALESCE(production_kind, 'crop'),
            product_name = COALESCE(product_name, crop_type),
            activity = COALESCE(
                activity,
                CASE
                    WHEN harvest_date IS NOT NULL OR quantity_kg IS NOT NULL
                        THEN 'harvest'
                    WHEN planted_date IS NOT NULL THEN 'planting'
                    ELSE NULL
                END
            ),
            unit = COALESCE(unit, 'kg'),
            expected_quantity = COALESCE(expected_quantity, expected_kg),
            quantity = COALESCE(quantity, quantity_kg),
            production_date = COALESCE(
                production_date,
                harvest_date,
                planted_date
            )
        """
    )

    with op.batch_alter_table("cooperative_memberships") as batch:
        batch.alter_column(
            "production_focus",
            existing_type=sa.String(),
            nullable=False,
            server_default="crop",
        )
    with op.batch_alter_table("productions") as batch:
        batch.alter_column(
            "production_kind",
            existing_type=sa.String(),
            nullable=False,
            server_default="crop",
        )
        batch.alter_column(
            "unit",
            existing_type=sa.String(),
            nullable=False,
            server_default="kg",
        )
        batch.alter_column(
            "crop_type",
            existing_type=sa.String(),
            nullable=True,
        )

    inspector = sa.inspect(op.get_bind())
    membership_checks = {
        check["name"]
        for check in inspector.get_check_constraints("cooperative_memberships")
    }
    if "ck_membership_production_focus" not in membership_checks:
        with op.batch_alter_table("cooperative_memberships") as batch:
            batch.create_check_constraint(
                "ck_membership_production_focus",
                "production_focus IN ('crop', 'animal', 'mixed')",
            )
    production_checks = {
        check["name"] for check in inspector.get_check_constraints("productions")
    }
    if "ck_production_kind" not in production_checks:
        with op.batch_alter_table("productions") as batch:
            batch.create_check_constraint(
                "ck_production_kind",
                "production_kind IN ('crop', 'animal')",
            )

    membership_indexes = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("cooperative_memberships")
    }
    if "ix_cooperative_memberships_production_focus" not in membership_indexes:
        op.create_index(
            "ix_cooperative_memberships_production_focus",
            "cooperative_memberships",
            ["production_focus"],
        )
    production_indexes = {
        index["name"]
        for index in sa.inspect(op.get_bind()).get_indexes("productions")
    }
    if "ix_productions_production_kind" not in production_indexes:
        op.create_index(
            "ix_productions_production_kind",
            "productions",
            ["production_kind"],
        )


def downgrade() -> None:
    op.drop_index(
        "ix_productions_production_kind",
        table_name="productions",
    )
    op.drop_index(
        "ix_cooperative_memberships_production_focus",
        table_name="cooperative_memberships",
    )
    # Animal rows may have NULL crop_type; restore a value before NOT NULL.
    op.execute(
        """
        UPDATE productions
        SET crop_type = COALESCE(crop_type, product_name, 'unknown')
        WHERE crop_type IS NULL
        """
    )
    with op.batch_alter_table("productions") as batch:
        batch.drop_constraint("ck_production_kind", type_="check")
        batch.alter_column(
            "crop_type",
            existing_type=sa.String(),
            nullable=False,
        )
        for column in (
            "production_date",
            "quantity",
            "expected_quantity",
            "unit",
            "activity",
            "product_name",
            "production_kind",
        ):
            batch.drop_column(column)
    with op.batch_alter_table("cooperative_memberships") as batch:
        batch.drop_constraint("ck_membership_production_focus", type_="check")
        batch.drop_column("animal_scale")
        batch.drop_column("animal_type")
        batch.drop_column("production_focus")
