"""SMS consent audit trail on cooperative memberships (#247).

Adds ``sms_consent_at`` and ``sms_opt_out_at`` so every consent change is
timestamped, and flips the *default* for new memberships from ``true`` to
``false`` — consent is now recorded explicitly at onboarding rather than
implied by membership (``docs/data-privacy.md`` §5.1).

Existing rows are **not** modified: memberships created before this
migration keep whatever ``sms_consent`` value they had (``true`` by the old
default). Operators who need to re-verify historic consent should do so
deliberately; the timestamps stay ``NULL`` for those rows to make them
identifiable.

Revision ID: 020_membership_consent_audit
Revises: 019_organizations
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect as sa_inspect

from alembic import op

revision: str = "020_membership_consent_audit"
down_revision: str | Sequence[str] | None = "019_organizations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_TABLE = "cooperative_memberships"


def _has_column(column: str) -> bool:
    inspector = sa_inspect(op.get_bind())
    if _TABLE not in inspector.get_table_names():
        return False
    return column in {c["name"] for c in inspector.get_columns(_TABLE)}


def upgrade() -> None:
    if not _has_column("sms_consent_at"):
        op.add_column(_TABLE, sa.Column("sms_consent_at", sa.DateTime(), nullable=True))
    if not _has_column("sms_opt_out_at"):
        op.add_column(_TABLE, sa.Column("sms_opt_out_at", sa.DateTime(), nullable=True))
    # New memberships default to no consent; existing rows are untouched.
    with op.batch_alter_table(_TABLE) as batch:
        batch.alter_column(
            "sms_consent",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=sa.false(),
        )


def downgrade() -> None:
    with op.batch_alter_table(_TABLE) as batch:
        batch.alter_column(
            "sms_consent",
            existing_type=sa.Boolean(),
            existing_nullable=False,
            server_default=sa.true(),
        )
        if _has_column("sms_opt_out_at"):
            batch.drop_column("sms_opt_out_at")
        if _has_column("sms_consent_at"):
            batch.drop_column("sms_consent_at")
