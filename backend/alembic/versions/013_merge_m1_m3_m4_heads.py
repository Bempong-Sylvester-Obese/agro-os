"""Merge M1, M3, and M4 migration heads.

Revision ID: 013_merge_m1_m3_m4
Revises: 012_ussd_session_state, 012_billing_entitlements, 012_coop_complete
"""

from collections.abc import Sequence


revision: str = "013_merge_m1_m3_m4"
down_revision: str | Sequence[str] | None = (
    "012_ussd_session_state",
    "012_billing_entitlements",
    "012_coop_complete",
)
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
