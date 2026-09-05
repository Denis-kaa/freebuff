"""Merge heads

Revision ID: 82a7cc8a277c
Revises: 08f68935afc8, add_review_status_to_orderstatus
Create Date: 2026-03-15 19:16:32.896510

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '82a7cc8a277c'
down_revision = ('08f68935afc8', 'add_review_status_to_orderstatus')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass

