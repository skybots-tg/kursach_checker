from fastapi import APIRouter

from app.api.v1 import (
    admin,
    auth,
    checks,
    content,
    files,
    gosts,
    orders,
    payments,
    templates,
    universities,
)

api_router = APIRouter(prefix="/api")
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(universities.router, prefix="/universities", tags=["universities"])
api_router.include_router(gosts.router, prefix="/gosts", tags=["gosts"])
api_router.include_router(templates.router, prefix="/templates", tags=["templates"])
api_router.include_router(checks.router, prefix="/checks", tags=["checks"])
api_router.include_router(payments.router, prefix="/payments", tags=["payments"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
