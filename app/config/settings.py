import os
import sys
import logging
import secrets
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent

logger = logging.getLogger(__name__)

IS_RENDER = bool(os.environ.get("RENDER"))


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    SECRET_KEY: str = ""
    APP_PORT: int = 8000

    def model_post_init(self, __context) -> None:
        if not self.SECRET_KEY:
            self.SECRET_KEY = secrets.token_hex(32)
            if IS_RENDER:
                logger.warning(
                    "SECRET_KEY not set — generated ephemeral key. "
                    "Sessions will NOT survive deploys. "
                    "Set SECRET_KEY in your Render dashboard for persistence."
                )
            else:
                logger.info("SECRET_KEY not set — generated random key for development.")


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

    if IS_RENDER:
        logger.critical(
            "FATAL: DATABASE_URL is not set! "
            "Render requires a PostgreSQL database. "
            "Configure DATABASE_URL in your Render dashboard or render.yaml."
        )
        sys.exit(1)

    logger.warning("DATABASE_URL not set - using SQLite (data will be lost on deploy!)")
    return f"sqlite:///{BASE_DIR}/devjourney.db"
