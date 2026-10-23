from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки приложения, читаются из переменных окружения / .env."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Трекер финансов"
    debug: bool = False

    database_url: str = "postgresql+psycopg://finance:finance@localhost:5432/finance"

    # JWT (ЛР 1, NFR-1): фиксированный алгоритм подписи, короткоживущие токены
    jwt_secret_key: str = "change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30


@lru_cache
def get_settings() -> Settings:
    return Settings()
