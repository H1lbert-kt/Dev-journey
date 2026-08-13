"""add ondelete cascade to foreign keys

Revision ID: d5e6f7a8b9c0
Revises: c4d5e6f7a8b9
Create Date: 2026-08-10

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'd5e6f7a8b9c0'
down_revision = 'c4d5e6f7a8b9'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # SQLite doesn't support ALTER TABLE to modify foreign keys,
    # so we need to recreate the tables. However, since init_database()
    # already handles this via create_all, we only run this migration
    # for PostgreSQL on Render.
    
    # For PostgreSQL, drop and recreate foreign keys with CASCADE
    op.execute("""
        ALTER TABLE goals DROP CONSTRAINT IF EXISTS goals_phase_id_fkey,
        ADD CONSTRAINT goals_phase_id_fkey FOREIGN KEY (phase_id) REFERENCES phases(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE habits DROP CONSTRAINT IF EXISTS habits_user_id_fkey,
        ADD CONSTRAINT habits_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE subjects DROP CONSTRAINT IF EXISTS subjects_user_id_fkey,
        ADD CONSTRAINT subjects_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE flashcards DROP CONSTRAINT IF EXISTS flashcards_subject_id_fkey,
        ADD CONSTRAINT flashcards_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE flashcards DROP CONSTRAINT IF EXISTS flashcards_user_id_fkey,
        ADD CONSTRAINT flashcards_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE study_sessions DROP CONSTRAINT IF EXISTS study_sessions_user_id_fkey,
        ADD CONSTRAINT study_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_user_id_fkey,
        ADD CONSTRAINT projects_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE phases DROP CONSTRAINT IF EXISTS phases_user_id_fkey,
        ADD CONSTRAINT phases_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE calendar_days DROP CONSTRAINT IF EXISTS calendar_days_user_id_fkey,
        ADD CONSTRAINT calendar_days_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE simulados DROP CONSTRAINT IF EXISTS simulados_user_id_fkey,
        ADD CONSTRAINT simulados_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE achievements DROP CONSTRAINT IF EXISTS achievements_user_id_fkey,
        ADD CONSTRAINT achievements_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE subject_goals DROP CONSTRAINT IF EXISTS subject_goals_subject_id_fkey,
        ADD CONSTRAINT subject_goals_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE subject_goals DROP CONSTRAINT IF EXISTS subject_goals_user_id_fkey,
        ADD CONSTRAINT subject_goals_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE user_sessions DROP CONSTRAINT IF EXISTS user_sessions_user_id_fkey,
        ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE weekly_schedule DROP CONSTRAINT IF EXISTS weekly_schedule_user_id_fkey,
        ADD CONSTRAINT weekly_schedule_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    """)
    op.execute("""
        ALTER TABLE weekly_schedule DROP CONSTRAINT IF EXISTS weekly_schedule_subject_id_fkey,
        ADD CONSTRAINT weekly_schedule_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
    """)


def downgrade() -> None:
    # Revert to non-CASCADE foreign keys
    op.execute("""
        ALTER TABLE goals DROP CONSTRAINT IF EXISTS goals_phase_id_fkey,
        ADD CONSTRAINT goals_phase_id_fkey FOREIGN KEY (phase_id) REFERENCES phases(id)
    """)
    op.execute("""
        ALTER TABLE habits DROP CONSTRAINT IF EXISTS habits_user_id_fkey,
        ADD CONSTRAINT habits_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE subjects DROP CONSTRAINT IF EXISTS subjects_user_id_fkey,
        ADD CONSTRAINT subjects_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE flashcards DROP CONSTRAINT IF EXISTS flashcards_subject_id_fkey,
        ADD CONSTRAINT flashcards_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES subjects(id)
    """)
    op.execute("""
        ALTER TABLE flashcards DROP CONSTRAINT IF EXISTS flashcards_user_id_fkey,
        ADD CONSTRAINT flashcards_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE study_sessions DROP CONSTRAINT IF EXISTS study_sessions_user_id_fkey,
        ADD CONSTRAINT study_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE projects DROP CONSTRAINT IF EXISTS projects_user_id_fkey,
        ADD CONSTRAINT projects_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE phases DROP CONSTRAINT IF EXISTS phases_user_id_fkey,
        ADD CONSTRAINT phases_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE calendar_days DROP CONSTRAINT IF EXISTS calendar_days_user_id_fkey,
        ADD CONSTRAINT calendar_days_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE simulados DROP CONSTRAINT IF EXISTS simulados_user_id_fkey,
        ADD CONSTRAINT simulados_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE achievements DROP CONSTRAINT IF EXISTS achievements_user_id_fkey,
        ADD CONSTRAINT achievements_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE subject_goals DROP CONSTRAINT IF EXISTS subject_goals_subject_id_fkey,
        ADD CONSTRAINT subject_goals_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES subjects(id)
    """)
    op.execute("""
        ALTER TABLE subject_goals DROP CONSTRAINT IF EXISTS subject_goals_user_id_fkey,
        ADD CONSTRAINT subject_goals_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE user_sessions DROP CONSTRAINT IF EXISTS user_sessions_user_id_fkey,
        ADD CONSTRAINT user_sessions_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE weekly_schedule DROP CONSTRAINT IF EXISTS weekly_schedule_user_id_fkey,
        ADD CONSTRAINT weekly_schedule_user_id_fkey FOREIGN KEY (user_id) REFERENCES users(id)
    """)
    op.execute("""
        ALTER TABLE weekly_schedule DROP CONSTRAINT IF EXISTS weekly_schedule_subject_id_fkey,
        ADD CONSTRAINT weekly_schedule_subject_id_fkey FOREIGN KEY (subject_id) REFERENCES subjects(id)
    """)
