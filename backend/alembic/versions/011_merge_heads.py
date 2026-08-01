"""Merge divergent migration heads.

Revision ID: 011_merge_heads
Revises: 6b09fb369e72, 007_phase1
"""

from typing import Sequence, Union


revision: str = "011_merge_heads"
down_revision: Union[str, Sequence[str], None] = ("6b09fb369e72", "007_phase1")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
