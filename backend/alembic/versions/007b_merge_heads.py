"""merge heads: organization_type + farmer_self_service_reminders

Revision ID: 007b_merge_heads
Revises: 007_organization_type, 008_loan_rejection_reasons
Create Date: 2026-08-01
"""
from typing import Sequence, Union

revision: str = "007b_merge_heads"
down_revision: Union[str, Sequence[str], None] = (
    "007_organization_type",
    "008_loan_rejection_reasons",
)
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
