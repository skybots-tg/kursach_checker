from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.router import api_router
from app.core.config import settings
from app.db.init_db import create_tables


def create_app() -> FastAPI:
    app = FastAPI(title=settings.app_name)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router)
    app.mount("/static", StaticFiles(directory="web/static"), name="static")
    app.mount("/admin/assets", StaticFiles(directory="web/admin"), name="admin-assets")

    @app.on_event("startup")
    async def on_startup() -> None:
        if settings.init_db_on_startup:
            await create_tables()

    @app.get("/", tags=["web"])
    async def mini_app() -> FileResponse:
        return FileResponse("web/mini_app/index.html")

    @app.get("/admin", tags=["web"])
    async def admin_app() -> FileResponse:
        return FileResponse("web/admin/index.html")

    @app.get("/health", tags=["system"])
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()
