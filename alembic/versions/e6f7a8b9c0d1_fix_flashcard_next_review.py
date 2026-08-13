"""fix flashcard next_review nullable and add server default

Revision ID: e6f7a8b9c0d1
Revises: d5e6f7a8b9c0
Create Date: 2026-08-10

"""
from alembic import op
import sqlalchemy as sa
from datetime import datetime


# revision identifiers, used by Alembic.
revision = 'e6f7a8b9c0d1'
down_revision = 'd5e6f7a8b9c0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Update existing NULL next_review to now so NOT NULL constraint can be added
    op.execute(f"UPDATE flashcards SET next_review = '{datetime.now().isoformat()}' WHERE next_review IS NULL")

    # Make NOT NULL and add server default
    op.alter_column('flashcards', 'next_review',
                     nullable=False,
                     server_default=sa.func.now())


def downgrade() -> None:
    op.alter_column('flashcards', 'next_review',
                     nullable=True,
                     server_default=None)
