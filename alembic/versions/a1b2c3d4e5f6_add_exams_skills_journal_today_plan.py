"""add exams, skills, journal, today_plan, session types

Revision ID: a1b2c3d4e5f6
Revises: f4a8b2c9d0e1
Create Date: 2026-08-15

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'a1b2c3d4e5f6'
down_revision = 'f4a8b2c9d0e1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Exams table
    op.create_table('exams',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('organization', sa.String(200), nullable=True),
        sa.Column('position', sa.String(200), nullable=True),
        sa.Column('banca', sa.String(100), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='planejando'),
        sa.Column('exam_date', sa.Date(), nullable=True),
        sa.Column('salary', sa.String(50), nullable=True),
        sa.Column('vacancies', sa.Integer(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exams_id'), 'exams', ['id'], unique=False)

    # Exam subjects table
    op.create_table('exam_subjects',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('exam_id', sa.Integer(), sa.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(200), nullable=False),
        sa.Column('weight', sa.Float(), nullable=False, server_default='1.0'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_exam_subjects_id'), 'exam_subjects', ['id'], unique=False)

    # Skills table
    op.create_table('skills',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('category', sa.String(50), nullable=True, server_default='geral'),
        sa.Column('progress', sa.Float(), nullable=False, server_default='0.0'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_skills_id'), 'skills', ['id'], unique=False)

    # Journal entries table
    op.create_table('journal_entries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_journal_entries_id'), 'journal_entries', ['id'], unique=False)

    # Today plan items table
    op.create_table('today_plan_items',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(200), nullable=False),
        sa.Column('subject_id', sa.Integer(), sa.ForeignKey('subjects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('estimated_minutes', sa.Integer(), nullable=True),
        sa.Column('time_optional', sa.String(5), nullable=True),
        sa.Column('priority', sa.String(10), nullable=False, server_default='media'),
        sa.Column('completed', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('item_type', sa.String(20), nullable=False, server_default='estudo'),
        sa.Column('date', sa.Date(), nullable=False),
        sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_today_plan_items_id'), 'today_plan_items', ['id'], unique=False)

    # Add session_type, exam_id, project_id to study_sessions
    op.add_column('study_sessions', sa.Column('session_type', sa.String(20), nullable=True, server_default='estudo'))
    op.add_column('study_sessions', sa.Column('exam_id', sa.Integer(), sa.ForeignKey('exams.id', ondelete='SET NULL'), nullable=True))
    op.add_column('study_sessions', sa.Column('project_id', sa.Integer(), sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True))


def downgrade() -> None:
    op.drop_column('study_sessions', 'project_id')
    op.drop_column('study_sessions', 'exam_id')
    op.drop_column('study_sessions', 'session_type')
    op.drop_table('today_plan_items')
    op.drop_table('journal_entries')
    op.drop_table('skills')
    op.drop_table('exam_subjects')
    op.drop_table('exams')
