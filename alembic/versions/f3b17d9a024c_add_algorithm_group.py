"""Add SpeedCubeDB subgroup to algorithms.

Revision ID: f3b17d9a024c
Revises: d8e6c4be0380
Create Date: 2026-07-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3b17d9a024c"
down_revision: Union[str, Sequence[str], None] = "d8e6c4be0380"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A temporary default keeps existing installations valid until the seed
    # command replaces it with the group parsed from SpeedCubeDB.
    op.add_column(
        "algorithms",
        sa.Column("group", sa.String(length=100), nullable=False, server_default="Uncategorized"),
    )
    op.alter_column("algorithms", "group", server_default=None)


def downgrade() -> None:
    op.drop_column("algorithms", "group")
