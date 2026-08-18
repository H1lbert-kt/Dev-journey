"""add study_mode to content tables

Revision ID: g5h6i7j8k9l0
Revises: f4a8b2c9d0e1
Create Date: 2026-08-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'g5h6i7j8k9l0'
down_revision = 'f4a8b2c9d0e1'
branch_labels = None
depends_on = None

TABLES = [
    'subjects',
    'study_sessions',
    'simulados',
    'flashcards',
    'today_plan_items',
    'skills',
    'projects',
    'phases',
    'journal_entries',
    'exams',
    'subject_goals',
]


def upgrade() -> None:
    for table in TABLES:
        op.add_column(table, sa.Column('study_mode', sa.String(20), nullable=False, server_default='programacao'))


def downgrade() -> None:
    for table in reversed(TABLES):
        op.drop_column(table, 'study_mode')
