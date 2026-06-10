from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    SUPABASE_JWKS_URL: str
    DATABASE_URL: str
    ENV: Literal["dev", "prod"] = "dev"

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()  # ty: ignore[missing-argument]
