import logging
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from app.config.settings import resolve_database_url

logger = logging.getLogger(__name__)

DATABASE_URL = resolve_database_url()
IS_POSTGRESQL = DATABASE_URL.startswith("postgresql")

connect_args = {}
engine_kwargs = {
    "pool_pre_ping": True,
    "pool_size": 10,
    "max_overflow": 20,
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
    finally:
        db.close()
