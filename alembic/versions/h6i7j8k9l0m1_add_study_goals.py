"""add study_goals table and simulado exam_id

Revision ID: h6i7j8k9l0m1
Revises: g5h6i7j8k9l0
Create Date: 2026-08-18

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'h6i7j8k9l0m1'
down_revision = 'g5h6i7j8k9l0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'study_goals',
        sa.Column('id', sa.Integer(), primary_key=True, index=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('study_mode', sa.String(20), nullable=False, server_default='programacao'),
        sa.Column('goal_type', sa.String(20), nullable=False, server_default='concurso'),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('target_date', sa.Date(), nullable=True),
        sa.Column('exam_id', sa.Integer(), sa.ForeignKey('exams.id', ondelete='SET NULL'), nullable=True),
        sa.Column('vestibular_name', sa.String(200), nullable=True),
        sa.Column('vestibular_institution', sa.String(200), nullable=True),
        sa.Column('vestibular_course', sa.String(200), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )
    op.add_column('simulados', sa.Column('exam_id', sa.Integer(), sa.ForeignKey('exams.id', ondelete='SET NULL'), nullable=True))


def downgrade() -> None:
    op.drop_column('simulados', 'exam_id')
    op.drop_table('study_goals')
