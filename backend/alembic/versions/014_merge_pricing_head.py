"""Merge pricing and milestone migration heads.

Revision ID: 014_merge_pricing
Revises: 012_pending_checkouts, 013_merge_m1_m3_m4
"""

from collections.abc import Sequence


revision: str = "014_merge_pricing"
down_revision: str | Sequence[str] | None = (
    "012_pending_checkouts",
    "013_merge_m1_m3_m4",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
