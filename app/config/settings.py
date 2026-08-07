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
        extra="ignore",
    )

    SECRET_KEY: str = "devjourney-secret-key-change-in-production"
    APP_PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()


def resolve_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()

    if url:
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://"):
            logger.info(f"PostgreSQL connected: {url.split('@')[-1]}")
            return url
        logger.warning(f"Unrecognized DATABASE_URL scheme: {url[:30]}...")
        return url

    logger.warning("DATABASE_URL not set - using SQLite (data will be lost on deploy!)")
    return f"sqlite:///{BASE_DIR}/devjourney.db"
