import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.db.init_db import create_tables

logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    docs_kwargs = {} if settings.debug else {"docs_url": None, "redoc_url": None, "openapi_url": None}
    app = FastAPI(title=settings.app_name, **docs_kwargs)

    origins = settings.cors_origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
    app.mount("/admin/assets", StaticFiles(directory="web/admin"), name="admin-assets")

    @app.on_event("startup")
    async def on_startup() -> None:
        _validate_config()
        if settings.init_db_on_startup:
            await create_tables()

    @app.get("/admin", tags=["web"])
    async def admin_app() -> FileResponse:
        return FileResponse("web/admin/index.html")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/{path:path}", tags=["web"], include_in_schema=False)
    async def mini_app_spa(path: str) -> FileResponse:
        return FileResponse(
            "web/mini_app/index.html",
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )

    return app


def _validate_config() -> None:
    if settings.jwt_secret in ("change-me", ""):
        logger.warning("JWT_SECRET is using default value! Set a strong secret in .env")
    if settings.admin_jwt_secret in ("change-admin-me", ""):
        logger.warning("ADMIN_JWT_SECRET is using default value! Set a strong secret in .env")
    if not settings.telegram_bot_token:
        logger.warning("TELEGRAM_BOT_TOKEN is empty — Telegram auth will not work")
    if not settings.prodamus_secret_key:
        logger.warning("PRODAMUS_SECRET_KEY is empty — payment webhooks will be rejected")


app = create_app()
