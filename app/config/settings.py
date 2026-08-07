from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
    )

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/devjourney.db"
    SECRET_KEY: str = "devjourney-secret-key-change-in-production"

    # PostgreSQL specific
    POSTGRES_DB: str = "devjourney"
    POSTGRES_USER: str = "devjourney"
    POSTGRES_PASSWORD: str = "devjourney_secure_password"
    POSTGRES_PORT: int = 5432

    APP_PORT: int = 8000


@lru_cache
def get_settings() -> Settings:
    return Settings()
