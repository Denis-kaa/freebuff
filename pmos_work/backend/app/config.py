"""Конфигурация приложения.

Всё, что может быть настроено, — настраивается через переменные окружения
(с дефолтами для локальной разработки). Ничего не захардкожено в коде.
"""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Настройки PM OS.

    Все значения можно переопределить переменными окружения
    (например DATABASE_URL=postgresql+asyncpg://...).
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- БД ---
    database_url: str = "postgresql+asyncpg://pmos:pmos_dev@127.0.0.1:5432/pmos_db"

    # --- Приложение ---
    app_name: str = "PM OS — configurable workspace"
    api_prefix: str = "/api"
    debug: bool = True

    # --- CORS (для Next.js dev-сервера) ---
    cors_origins: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ]


@lru_cache
def get_settings() -> Settings:
    return Settings()
