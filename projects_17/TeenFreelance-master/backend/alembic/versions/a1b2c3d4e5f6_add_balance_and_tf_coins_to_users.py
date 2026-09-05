"""add balance and tf_coins to users

Revision ID: a1b2c3d4e5f6
Revises: ce6f319d1692
Create Date: 2026-04-12 22:37:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'ce6f319d1692'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('balance', sa.Float(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('tf_coins', sa.Integer(), nullable=False, server_default='0'))


def downgrade() -> None:
    op.drop_column('users', 'tf_coins')
    op.drop_column('users', 'balance')
