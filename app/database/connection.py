import logging
from sqlalchemy import create_engine, event, text, inspect
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config.settings import resolve_database_url, IS_RENDER

logger = logging.getLogger(__name__)

DATABASE_URL = resolve_database_url()
IS_POSTGRESQL = DATABASE_URL.startswith("postgresql")

connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_recycle": 300,
}

if not IS_POSTGRESQL:
    connect_args["check_same_thread"] = False
    engine_kwargs.pop("pool_size")
    engine_kwargs.pop("max_overflow")

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs
)

if not IS_POSTGRESQL:
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        try:
            db.rollback()
        except Exception:
            pass
        raise
    finally:
        db.close()


def init_database():
    """Create tables and add missing columns. Safe for multi-worker startup."""
    from app.models import User, Phase, Goal, Project, Habit, CalendarDay
    from app.models import Achievement, StudySession, Subject, Flashcard, FlashcardReview
    from app.models import Simulado, SubjectGoal, UserSession, WeeklySchedule
    from app.models import Exam, ExamSubject, Skill, JournalEntry, TodayPlanItem

    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()

    required_tables = [
        "users", "user_sessions", "phases", "goals", "projects",
        "habits", "calendar_days", "achievements", "study_sessions",
        "subjects", "flashcards", "flashcard_reviews", "simulados", "subject_goals",
        "weekly_schedule", "exams", "exam_subjects", "skills",
        "journal_entries", "today_plan_items",
    ]

    missing_tables = [t for t in required_tables if t not in existing_tables]

    if missing_tables:
        if IS_POSTGRESQL and IS_RENDER:
            _create_with_pg_advisory_lock(missing_tables)
        else:
            _create_tables(missing_tables)
    else:
        logger.info("All database tables already exist.")

    _add_missing_columns(inspector)


def _add_missing_columns(inspector):
    """Add any columns that exist in models but not in the database."""
    columns_map = {
        "simulados": [
            ("wrong_answers", "INTEGER", "0"),
            ("null_answers", "INTEGER", "0"),
            ("correction_method", "VARCHAR(20)", "'normal'"),
            ("final_score", "FLOAT", None),
            ("display_order", "INTEGER", "0"),
            ("study_mode", "VARCHAR(20)", "'programacao'"),
            ("exam_id", "INTEGER", None),
        ],
        "subjects": [
            ("color", "VARCHAR(7)", "'#58a6ff'"),
            ("study_mode", "VARCHAR(20)", "'programacao'"),
        ],
        "weekly_schedule": [
            ("order", "INTEGER", "0"),
        ],
        "users": [
            ("timer_state_seconds", "INTEGER", "0"),
            ("timer_state_subject", "VARCHAR(100)", "''"),
            ("daily_goal_minutes", "INTEGER", "360"),
        ],
        "study_sessions": [
            ("session_type", "VARCHAR(20)", "'estudo'"),
            ("exam_id", "INTEGER", None),
            ("project_id", "INTEGER", None),
            ("study_mode", "VARCHAR(20)", "'programacao'"),
        ],
        "flashcards": [
            ("study_mode", "VARCHAR(20)", "'programacao'"),
            ("review_count", "INTEGER", "0"),
            ("streak", "INTEGER", "0"),
            ("last_reviewed_at", "TIMESTAMP", None),
        ],
        "today_plan_items": [
            ("study_mode", "VARCHAR(20)", "'programacao'"),
        ],
        "skills": [
            ("study_mode", "VARCHAR(20)", "'programacao'"),
        ],
        "projects": [
            ("study_mode", "VARCHAR(20)", "'programacao'"),
        ],
        "phases": [
            ("study_mode", "VARCHAR(20)", "'programacao'"),
        ],
        "journal_entries": [
            ("study_mode", "VARCHAR(20)", "'programacao'"),
        ],
        "exams": [
            ("study_mode", "VARCHAR(20)", "'programacao'"),
        ],
        "subject_goals": [
            ("study_mode", "VARCHAR(20)", "'programacao'"),
        ],
    }

    for table_name, expected_columns in columns_map.items():
        if table_name not in inspector.get_table_names():
            continue

        existing_cols = {c["name"] for c in inspector.get_columns(table_name)}

        for col_name, col_type, default_val in expected_columns:
            if col_name not in existing_cols:
                try:
                    sql = f"ALTER TABLE {table_name} ADD COLUMN {col_name} {col_type}"
                    if default_val is not None:
                        sql += f" DEFAULT {default_val}"
                    with engine.begin() as conn:
                        conn.execute(text(sql))
                    logger.info(f"Added missing column {table_name}.{col_name}")
                except Exception as e:
                    if "already exists" in str(e).lower():
                        pass
                    else:
                        logger.warning(f"Could not add column {table_name}.{col_name}: {e}")


def _create_with_pg_advisory_lock(missing):
    """Use PostgreSQL advisory lock to ensure only one worker creates tables."""
    with engine.connect() as conn:
        try:
            conn.execute(text("SELECT pg_advisory_lock(12345)"))
            logger.info("Acquired advisory lock for table creation.")

            existing = inspect(engine).get_table_names()
            still_missing = [t for t in missing if t not in existing]

            if still_missing:
                logger.info(f"Creating missing tables: {still_missing}")
                Base.metadata.create_all(bind=engine)
                logger.info("Tables created successfully.")
            else:
                logger.info("Tables were created by another worker.")

            conn.execute(text("SELECT pg_advisory_unlock(12345)"))
            logger.info("Released advisory lock.")
        except Exception as e:
            try:
                conn.execute(text("SELECT pg_advisory_unlock(12345)"))
            except Exception:
                pass
            logger.error(f"Advisory lock failed: {e}")
            logger.info("Falling back to direct create_all...")
            Base.metadata.create_all(bind=engine)


def _create_tables(missing):
    """Create tables directly (single worker / SQLite)."""
    logger.info(f"Creating missing tables: {missing}")
    Base.metadata.create_all(bind=engine)
    logger.info("Tables created successfully.")
