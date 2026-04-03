from fastapi import APIRouter

from app.api.v1 import (
    admin,
    admin_analytics,
    admin_autofix,
    admin_checks,
    admin_content,
    admin_content_messages,
    admin_demo,
    admin_orders,
    admin_products,
    admin_settings,
    admin_users,
    auth,
    checks,
    content,
    credits,
    demo,
    files,
    gosts,
    orders,
    payments,
    products,
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
api_router.include_router(credits.router, prefix="/credits", tags=["credits"])
api_router.include_router(orders.router, prefix="/orders", tags=["orders"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(content.router, prefix="/content", tags=["content"])
api_router.include_router(demo.router, prefix="/demo", tags=["demo"])
api_router.include_router(products.router, prefix="/products", tags=["products"])
api_router.include_router(admin.router, prefix="/admin", tags=["admin"])
api_router.include_router(admin_products.router, prefix="/admin/products", tags=["admin-products"])
api_router.include_router(admin_orders.router, prefix="/admin/orders", tags=["admin-orders"])
api_router.include_router(admin_checks.router, prefix="/admin/checks", tags=["admin-checks"])
api_router.include_router(admin_users.router, prefix="/admin/users", tags=["admin-users"])
api_router.include_router(admin_demo.router, prefix="/admin/demo", tags=["admin-demo"])
api_router.include_router(admin_content.router, prefix="/admin/content", tags=["admin-content"])
api_router.include_router(admin_content_messages.router, prefix="/admin/content", tags=["admin-content-messages"])
api_router.include_router(admin_autofix.router, prefix="/admin/autofix", tags=["admin-autofix"])
api_router.include_router(admin_settings.router, prefix="/admin/settings", tags=["admin-settings"])
api_router.include_router(admin_analytics.router, prefix="/admin/analytics", tags=["admin-analytics"])
