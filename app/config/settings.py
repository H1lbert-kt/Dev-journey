import os
import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/devjourney.db"
    SECRET_KEY: str = "devjourney-secret-key-change-in-production"

    POSTGRES_DB: str = "devjourney"
    POSTGRES_USER: str = "devjourney"
    POSTGRES_PASSWORD: str = "devjourney_secure_password"
    POSTGRES_PORT: int = 5432

    APP_PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "")

    if not url:
        logger.warning("DATABASE_URL not set, falling back to SQLite")
        return f"sqlite:///{BASE_DIR}/devjourney.db"

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
        logger.info("Fixed postgres:// -> postgresql://")

    logger.info(f"Using database: {url.split('@')[-1] if '@' in url else url}")
    return url
