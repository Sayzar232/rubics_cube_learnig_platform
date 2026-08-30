"""add is_verified to users

Revision ID: f3a7c1d92b54
Revises: f3b17d9a024c
Create Date: 2026-08-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a7c1d92b54'
down_revision: Union[str, Sequence[str], None] = 'f3b17d9a024c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'users',
        sa.Column('is_verified', sa.Boolean(), nullable=False, server_default=sa.text('false')),
    )
    # Существующие аккаунты считаем подтверждёнными,
    # иначе новая проверка заблокирует им вход.
    op.execute('UPDATE users SET is_verified = true')


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('users', 'is_verified')