from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env")

    DATABASE_URL: str = f"sqlite:///{BASE_DIR}/devjourney.db"
    SECRET_KEY: str = "devjourney-secret-key-change-in-production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
