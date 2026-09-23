"""Enterprise organizations: parent account for many cooperatives (#237).

Creates ``organizations`` and adds nullable ``organization_id`` foreign keys
to ``cooperatives`` (membership) and ``users`` (organization administrators).
Existing rows are unaffected: independent cooperatives keep ``NULL``.

Revision ID: 019_organizations
Revises: 018_subscription_intents
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

revision: str = "019_organizations"
down_revision: str | Sequence[str] | None = "018_subscription_intents"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ORG = "organizations"
_FK_COOP = "fk_cooperatives_organization_id"
_IX_COOP = "ix_cooperatives_organization_id"
_FK_USER = "fk_users_organization_id"
_IX_USER = "ix_users_organization_id"


def _inspector():
    return sa_inspect(op.get_bind())


def _has_column(table: str, column: str) -> bool:
    inspector = _inspector()
    if table not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    inspector = _inspector()
    if _ORG not in inspector.get_table_names():
        op.create_table(
            _ORG,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("billing_email", sa.String(), nullable=True),
            sa.Column(
                "subscription_plan", sa.String(), nullable=False, server_default="enterprise"
            ),
            sa.Column(
                "subscription_status", sa.String(), nullable=False, server_default="pending"
            ),
            sa.Column("subscription_expires_at", sa.DateTime(), nullable=True),
            sa.Column("contract_reference", sa.String(), nullable=True),
            sa.Column(
                "created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()
            ),
            sa.Column("updated_at", sa.DateTime(), nullable=True),
        )
        op.create_index("ix_organizations_id", _ORG, ["id"])
        op.create_index("ix_organizations_name", _ORG, ["name"])

    if not _has_column("cooperatives", "organization_id"):
        op.add_column("cooperatives", sa.Column("organization_id", sa.Integer(), nullable=True))
        op.create_index(_IX_COOP, "cooperatives", ["organization_id"])
        op.create_foreign_key(
            _FK_COOP, "cooperatives", _ORG, ["organization_id"], ["id"], ondelete="SET NULL"
        )

    if not _has_column("users", "organization_id"):
        op.add_column("users", sa.Column("organization_id", sa.Integer(), nullable=True))
        op.create_index(_IX_USER, "users", ["organization_id"])
        op.create_foreign_key(
            _FK_USER, "users", _ORG, ["organization_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    if _has_column("users", "organization_id"):
        with op.batch_alter_table("users") as batch:
            batch.drop_constraint(_FK_USER, type_="foreignkey")
            batch.drop_index(_IX_USER)
            batch.drop_column("organization_id")
    if _has_column("cooperatives", "organization_id"):
        with op.batch_alter_table("cooperatives") as batch:
            batch.drop_constraint(_FK_COOP, type_="foreignkey")
            batch.drop_index(_IX_COOP)
            batch.drop_column("organization_id")
    if _ORG in _inspector().get_table_names():
        op.drop_index("ix_organizations_name", table_name=_ORG)
        op.drop_index("ix_organizations_id", table_name=_ORG)
        op.drop_table(_ORG)
