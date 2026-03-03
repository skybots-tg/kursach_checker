from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Курсач Чекер"
    app_host: str = "0.0.0.0"
    app_port: int = 8343
    app_reload: bool = False

    database_url: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/kursach"
    redis_url: str = "redis://localhost:6379/0"

    jwt_secret: str = "change-me"
    jwt_algorithm: str = "HS256"

    telegram_bot_token: str = ""
    telegram_bot_username: str = ""

    prodamus_secret_key: str = ""
    prodamus_shop_id: str = ""

    admin_jwt_secret: str = "change-admin-me"
    init_db_on_startup: bool = False


settings = Settings()

