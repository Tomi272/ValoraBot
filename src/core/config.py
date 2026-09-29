# Archivo: src/core/config.py
from functools import lru_cache
from pathlib import Path

from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE: Path = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    """Sin valores por defecto para secretos: si falta el .env, la app no arranca."""

    model_config = SettingsConfigDict(env_file=_ENV_FILE, env_file_encoding="utf-8", extra="ignore")

    database_url: str
    jwt_secret_key: SecretStr
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    celery_broker_url: str = "redis://localhost:6379/0"

    @field_validator("jwt_secret_key")
    @classmethod
    def _secret_min_length(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY debe tener al menos 32 caracteres.")
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]