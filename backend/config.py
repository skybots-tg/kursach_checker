from __future__ import annotations

from functools import lru_cache
from pydantic import PostgresDsn, RedisDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Глобальные настройки backend‑сервиса."""

    app_name: str = "Kursach Checker"
    debug: bool = False

    # База данных
    database_dsn: PostgresDsn = "postgresql+asyncpg://user:password@localhost:5432/kursach_checker"  # type: ignore[assignment]

    # Redis / очередь задач
    redis_dsn: RedisDsn = "redis://localhost:6379/0"  # type: ignore[assignment]

    # CORS для Mini App / админки
    allowed_origins: list[str] = ["*"]

    # JWT/сессии Mini App
    jwt_secret: str = "CHANGE_ME_SECRET"
    jwt_algorithm: str = "HS256"
    jwt_ttl_seconds: int = 60 * 60 * 24 * 30

    # Telegram / Prodamus интеграции
    telegram_bot_token: str = "CHANGE_ME_BOT_TOKEN"
    prodamus_payment_base_url: str = "https://pay.example.com"

    # Демо‑отчёт для Mini App (предзагруженный JSON CheckReport).
    demo_report_path: str | None = "rules_specs/demo_report_hse_journalism_2024_25.json"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()


