"""add weekly_schedule table

Revision ID: b390de3ff540
Revises: 930b5d030966
Create Date: 2026-08-10 15:56:41.347456

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = 'b390de3ff540'
down_revision: Union[str, None] = '930b5d030966'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'weekly_schedule',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('subject_id', sa.Integer(), nullable=False),
        sa.Column('day_of_week', sa.Integer(), nullable=False),
        sa.Column('order', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=True),
        sa.ForeignKeyConstraint(['subject_id'], ['subjects.id']),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('user_id', 'subject_id', 'day_of_week', name='uq_user_subject_day'),
    )
    op.create_index('ix_weekly_schedule_id', 'weekly_schedule', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_weekly_schedule_id', table_name='weekly_schedule')
    op.drop_table('weekly_schedule')
