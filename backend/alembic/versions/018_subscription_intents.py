"""Turn pending_checkouts into general single-use subscription payment intents.

Adds the columns needed for authenticated upgrade intents (``sub_upg_*``):
kind, cooperative_id, created_by_user_id, provider_transaction_id, paid_at,
consumed_at; and relaxes ``organisation`` to nullable because an upgrade
intent belongs to an existing cooperative.

Revision ID: 018_subscription_intents
Revises: 017_wage_payout_ref
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

revision: str = "018_subscription_intents"
down_revision: str | Sequence[str] | None = "017_wage_payout_ref"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "pending_checkouts"
_FK_COOP = "fk_pending_checkouts_cooperative_id"
_FK_USER = "fk_pending_checkouts_created_by_user_id"
_IX_COOP = "ix_pending_checkouts_cooperative_id"


def _columns() -> set[str]:
    inspector = sa_inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return set()
    return {c["name"] for c in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    existing = _columns()
    if not existing:
        return

    if "kind" not in existing:
        op.add_column(
            _TABLE,
            sa.Column(
                "kind", sa.String(), nullable=False, server_default="pre_checkout"
            ),
        )
    if "cooperative_id" not in existing:
        op.add_column(_TABLE, sa.Column("cooperative_id", sa.Integer(), nullable=True))
        op.create_index(_IX_COOP, _TABLE, ["cooperative_id"])
        op.create_foreign_key(
            _FK_COOP, _TABLE, "cooperatives", ["cooperative_id"], ["id"], ondelete="SET NULL"
        )
    if "created_by_user_id" not in existing:
        op.add_column(_TABLE, sa.Column("created_by_user_id", sa.Integer(), nullable=True))
        op.create_foreign_key(
            _FK_USER, _TABLE, "users", ["created_by_user_id"], ["id"], ondelete="SET NULL"
        )
    if "provider_transaction_id" not in existing:
        op.add_column(
            _TABLE, sa.Column("provider_transaction_id", sa.String(), nullable=True)
        )
    if "paid_at" not in existing:
        op.add_column(_TABLE, sa.Column("paid_at", sa.DateTime(), nullable=True))
    if "consumed_at" not in existing:
        op.add_column(_TABLE, sa.Column("consumed_at", sa.DateTime(), nullable=True))

    op.alter_column(_TABLE, "organisation", existing_type=sa.String(), nullable=True)


def downgrade() -> None:
    existing = _columns()
    if not existing:
        return

    # Upgrade intents have no organisation; give them one before re-tightening.
    op.execute(
        sa.text(
            f"UPDATE {_TABLE} SET organisation = 'upgrade' WHERE organisation IS NULL"
        )
    )
    op.alter_column(_TABLE, "organisation", existing_type=sa.String(), nullable=False)

    for column in ("consumed_at", "paid_at", "provider_transaction_id"):
        if column in existing:
            op.drop_column(_TABLE, column)
    if "created_by_user_id" in existing:
        op.drop_constraint(_FK_USER, _TABLE, type_="foreignkey")
        op.drop_column(_TABLE, "created_by_user_id")
    if "cooperative_id" in existing:
        op.drop_constraint(_FK_COOP, _TABLE, type_="foreignkey")
        op.drop_index(_IX_COOP, table_name=_TABLE)
        op.drop_column(_TABLE, "cooperative_id")
    if "kind" in existing:
        op.drop_column(_TABLE, "kind")
