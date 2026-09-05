"""add review status to orderstatus enum

Revision ID: add_review_status_to_orderstatus
Revises: cb8d7b554c2b
Create Date: 2026-01-27
"""

from alembic import op

# revision identifiers, used by Alembic.
revision = "add_review_status_to_orderstatus"
down_revision = "cb8d7b554c2b"
branch_labels = None
depends_on = None


def upgrade() -> None:
  # Для PostgreSQL: добавляем новое значение в Enum orderstatus.
  # В рабочей базе статусы хранятся в lowercase ('draft', 'open', 'in_progress', ...),
  # поэтому добавляем 'review' (lowercase), чтобы не ломать существующие данные.
  op.execute("ALTER TYPE orderstatus ADD VALUE IF NOT EXISTS 'review';")


def downgrade() -> None:
  # Откат для ENUM в PostgreSQL сложен, оставляем как no-op,
  # так как удаление значения из enum небезопасно.
  pass

