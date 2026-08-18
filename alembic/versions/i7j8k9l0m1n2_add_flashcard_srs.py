"""add flashcard SRS fields and flashcard_reviews table

Revision ID: i7j8k9l0m1n2
Revises: h6i7j8k9l0m1
Create Date: 2026-08-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'i7j8k9l0m1n2'
down_revision = 'h6i7j8k9l0m1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('flashcards', sa.Column('review_count', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('flashcards', sa.Column('streak', sa.Integer(), nullable=False, server_default='0'))
    op.add_column('flashcards', sa.Column('last_reviewed_at', sa.DateTime(), nullable=True))

    op.create_table(
        'flashcard_reviews',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('flashcard_id', sa.Integer(), sa.ForeignKey('flashcards.id', ondelete='CASCADE'), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('quality', sa.Integer(), nullable=False),
        sa.Column('interval_before', sa.Integer(), nullable=False),
        sa.Column('interval_after', sa.Integer(), nullable=False),
        sa.Column('ease_factor_before', sa.Float(), nullable=False),
        sa.Column('ease_factor_after', sa.Float(), nullable=False),
        sa.Column('study_mode', sa.String(20), nullable=False, server_default='programacao'),
        sa.Column('reviewed_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.create_index('ix_flashcard_reviews_flashcard_id', 'flashcard_reviews', ['flashcard_id'])
    op.create_index('ix_flashcard_reviews_user_id', 'flashcard_reviews', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_flashcard_reviews_user_id')
    op.drop_index('ix_flashcard_reviews_flashcard_id')
    op.drop_table('flashcard_reviews')
    op.drop_column('flashcards', 'last_reviewed_at')
    op.drop_column('flashcards', 'streak')
    op.drop_column('flashcards', 'review_count')
