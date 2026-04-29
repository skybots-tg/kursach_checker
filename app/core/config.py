from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Курсач Чекер"
    app_host: str = "0.0.0.0"
    app_port: int = 8343
    app_reload: bool = False
    app_base_url: str = "https://example.com"
    debug: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kursach"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"
    jwt_expire_hours: int = 24
    admin_jwt_expire_hours: int = 8

    telegram_bot_token: str = ""
    telegram_bot_username: str = ""
    telegram_auth_max_age_sec: int = 86400

    # Бонус за подписку на канал (необязательно). Если задан username канала
    # и бот добавлен туда как администратор, у пользователя появляется
    # кнопка «Получить +N за подписку», бонус выдаётся один раз.
    subscribe_bonus_channel_username: str = ""
    subscribe_bonus_amount: int = 2

    prodamus_secret_key: str = ""
    prodamus_payform_url: str = "https://payform.prodamus.ru"
    prodamus_timeout_sec: int = 30

    admin_jwt_secret: str = "change-admin-me"
    init_db_on_startup: bool = False

    allowed_origins: str = ""
    max_upload_mb: int = 20

    doc_to_docx_converter: str = ""

    @property
    def cors_origins(self) -> list[str]:
        if self.allowed_origins:
            return [o.strip() for o in self.allowed_origins.split(",") if o.strip()]
        if self.debug:
            return ["*"]
        return [self.app_base_url]


settings = Settings()
