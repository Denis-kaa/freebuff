"""add_text_message_type

Revision ID: 08f68935afc8
Revises: 5940efc5a86a
Create Date: 2026-01-25 19:06:03.409299

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '08f68935afc8'
down_revision = '5940efc5a86a'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Добавляем новый тип 'text' в enum messagetype
    op.execute("ALTER TYPE messagetype ADD VALUE IF NOT EXISTS 'text'")


def downgrade() -> None:
    # В PostgreSQL нельзя удалить значение из enum, поэтому оставляем пустым
    pass

