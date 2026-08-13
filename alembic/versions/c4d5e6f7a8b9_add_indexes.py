"""add user_id indexes

Revision ID: c4d5e6f7a8b9
Revises: b390de3ff540
Create Date: 2026-08-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c4d5e6f7a8b9'
down_revision = 'b390de3ff540'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index('ix_habits_user_id', 'habits', ['user_id'])
    op.create_index('ix_projects_user_id', 'projects', ['user_id'])
    op.create_index('ix_study_sessions_user_id', 'study_sessions', ['user_id'])
    op.create_index('ix_subjects_user_id', 'subjects', ['user_id'])
    op.create_index('ix_flashcards_user_id', 'flashcards', ['user_id'])
    op.create_index('ix_simulados_user_id', 'simulados', ['user_id'])
    op.create_index('ix_user_sessions_user_id', 'user_sessions', ['user_id'])
    op.create_index('ix_weekly_schedule_user_id', 'weekly_schedule', ['user_id'])
    op.create_index('ix_subject_goals_user_id', 'subject_goals', ['user_id'])
    op.create_index('ix_achievements_user_id', 'achievements', ['user_id'])
    op.create_index('ix_calendar_days_user_id', 'calendar_days', ['user_id'])


def downgrade() -> None:
    op.drop_index('ix_calendar_days_user_id', 'calendar_days')
    op.drop_index('ix_achievements_user_id', 'achievements')
    op.drop_index('ix_subject_goals_user_id', 'subject_goals')
    op.drop_index('ix_weekly_schedule_user_id', 'weekly_schedule')
    op.drop_index('ix_user_sessions_user_id', 'user_sessions')
    op.drop_index('ix_simulados_user_id', 'simulados')
    op.drop_index('ix_flashcards_user_id', 'flashcards')
    op.drop_index('ix_subjects_user_id', 'subjects')
    op.drop_index('ix_study_sessions_user_id', 'study_sessions')
    op.drop_index('ix_projects_user_id', 'projects')
    op.drop_index('ix_habits_user_id', 'habits')
