from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_session
from backend.db.models_domain import BotContent, Check, Template, TemplateVersion, University, Gost
from backend.db.models_users import AuditLog, Order, Product, ProdamusPayment
from backend.schemas.admin import (
    AuditLogItem,
    BotContentCreateUpdate,
    BotContentItem,
    CheckItemAdmin,
    GostCreateUpdate,
    GostItem,
    OrderItemAdmin,
    ProductCreateUpdate,
    ProductItem,
    ProdamusPaymentItem,
    TemplateCreateUpdate,
    TemplateItem,
    TemplateVersionCreate,
    TemplateVersionDetail,
    TemplateVersionItem,
    TemplateVersionUpdate,
    UniversityCreateUpdate,
    UniversityItem,
)
from backend.rules_engine.schemas import TemplateRulesConfig


router = APIRouter(prefix="/api/admin", tags=["admin"])


@router.get("/health")
async def healthcheck() -> dict[str, str]:
    """Простой healthcheck для админки/оркестрации."""
    return {"status": "ok"}


@router.get("/universities", response_model=list[UniversityItem])
async def list_universities(session: AsyncSession = Depends(get_session)) -> list[UniversityItem]:
    stmt = select(University).order_by(University.priority, University.name)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        UniversityItem(
            id=u.id,
            name=u.name,
            active=u.active,
            description=u.description,
            priority=u.priority,
        )
        for u in rows
    ]


@router.post("/universities", response_model=UniversityItem, status_code=status.HTTP_201_CREATED)
async def create_university(
    payload: UniversityCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> UniversityItem:
    uni = University(
        name=payload.name,
        active=payload.active,
        description=payload.description,
        priority=payload.priority,
    )
    session.add(uni)
    await session.flush()
    return UniversityItem(
        id=uni.id,
        name=uni.name,
        active=uni.active,
        description=uni.description,
        priority=uni.priority,
    )


@router.put("/universities/{university_id}", response_model=UniversityItem)
async def update_university(
    university_id: int,
    payload: UniversityCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> UniversityItem:
    stmt = select(University).where(University.id == university_id)
    result = await session.execute(stmt)
    uni = result.scalar_one_or_none()
    if uni is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="University not found")

    uni.name = payload.name
    uni.active = payload.active
    uni.description = payload.description
    uni.priority = payload.priority
    await session.flush()
    return UniversityItem(
        id=uni.id,
        name=uni.name,
        active=uni.active,
        description=uni.description,
        priority=uni.priority,
    )


@router.get("/gosts", response_model=list[GostItem])
async def list_gosts(session: AsyncSession = Depends(get_session)) -> list[GostItem]:
    stmt = select(Gost).order_by(Gost.name)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        GostItem(
            id=g.id,
            name=g.name,
            description=g.description,
            active=g.active,
            type=g.type,
            year=g.year,
        )
        for g in rows
    ]


@router.post("/gosts", response_model=GostItem, status_code=status.HTTP_201_CREATED)
async def create_gost(
    payload: GostCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> GostItem:
    gost = Gost(
        name=payload.name,
        description=payload.description,
        active=payload.active,
        type=payload.type,
        year=payload.year,
    )
    session.add(gost)
    await session.flush()
    return GostItem(
        id=gost.id,
        name=gost.name,
        description=gost.description,
        active=gost.active,
        type=gost.type,
        year=gost.year,
    )


@router.put("/gosts/{gost_id}", response_model=GostItem)
async def update_gost(
    gost_id: int,
    payload: GostCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> GostItem:
    stmt = select(Gost).where(Gost.id == gost_id)
    result = await session.execute(stmt)
    gost = result.scalar_one_or_none()
    if gost is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Gost not found")

    gost.name = payload.name
    gost.description = payload.description
    gost.active = payload.active
    gost.type = payload.type
    gost.year = payload.year
    await session.flush()
    return GostItem(
        id=gost.id,
        name=gost.name,
        description=gost.description,
        active=gost.active,
        type=gost.type,
        year=gost.year,
    )


@router.get("/templates", response_model=list[TemplateItem])
async def list_templates(session: AsyncSession = Depends(get_session)) -> list[TemplateItem]:
    stmt = select(Template).order_by(Template.name)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        TemplateItem(
            id=t.id,
            university_id=t.university_id,
            name=t.name,
            type_work=t.type_work,
            year=t.year,
            status=t.status,
            active=t.active,
        )
        for t in rows
    ]


@router.post("/templates", response_model=TemplateItem, status_code=status.HTTP_201_CREATED)
async def create_template(
    payload: TemplateCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> TemplateItem:
    template = Template(
        university_id=payload.university_id,
        name=payload.name,
        type_work=payload.type_work,
        year=payload.year,
        status=payload.status,
        active=payload.active,
    )
    session.add(template)
    await session.flush()
    return TemplateItem(
        id=template.id,
        university_id=template.university_id,
        name=template.name,
        type_work=template.type_work,
        year=template.year,
        status=template.status,
        active=template.active,
    )


@router.put("/templates/{template_id}", response_model=TemplateItem)
async def update_template(
    template_id: int,
    payload: TemplateCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> TemplateItem:
    stmt = select(Template).where(Template.id == template_id)
    result = await session.execute(stmt)
    template = result.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    template.university_id = payload.university_id
    template.name = payload.name
    template.type_work = payload.type_work
    template.year = payload.year
    template.status = payload.status
    template.active = payload.active
    await session.flush()
    return TemplateItem(
        id=template.id,
        university_id=template.university_id,
        name=template.name,
        type_work=template.type_work,
        year=template.year,
        status=template.status,
        active=template.active,
    )


@router.get("/templates/{template_id}/versions", response_model=list[TemplateVersionItem])
async def list_template_versions(
    template_id: int,
    session: AsyncSession = Depends(get_session),
) -> list[TemplateVersionItem]:
    stmt = (
        select(TemplateVersion)
        .where(TemplateVersion.template_id == template_id)
        .order_by(TemplateVersion.version_number.desc())
    )
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        TemplateVersionItem(
            id=v.id,
            template_id=v.template_id,
            version_number=v.version_number,
            created_at=v.created_at,
            created_by_admin_id=v.created_by_admin_id,
        )
        for v in rows
    ]


@router.post(
    "/templates/{template_id}/versions",
    response_model=TemplateVersionDetail,
    status_code=status.HTTP_201_CREATED,
)
async def create_template_version(
    template_id: int,
    payload: TemplateVersionCreate,
    session: AsyncSession = Depends(get_session),
) -> TemplateVersionDetail:
    # Убедимся, что шаблон существует.
    stmt_template = select(Template).where(Template.id == template_id)
    result_template = await session.execute(stmt_template)
    template = result_template.scalar_one_or_none()
    if template is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template not found")

    # Автонаращивание версии.
    stmt_max = select(func.max(TemplateVersion.version_number)).where(TemplateVersion.template_id == template_id)
    result_max = await session.execute(stmt_max)
    max_version = result_max.scalar_one()
    next_version = (max_version or 0) + 1

    # Валидация rules через TemplateRulesConfig уже происходит в pydantic‑схеме payload.rules.
    rules_dict = payload.rules.model_dump(mode="json")

    version = TemplateVersion(
        template_id=template_id,
        version_number=next_version,
        rules_json=rules_dict,
        created_by_admin_id=None,
    )
    session.add(version)
    await session.flush()

    return TemplateVersionDetail(
        id=version.id,
        template_id=version.template_id,
        version_number=version.version_number,
        created_at=version.created_at,
        created_by_admin_id=version.created_by_admin_id,
        rules=payload.rules,
    )


@router.get("/template_versions/{version_id}", response_model=TemplateVersionDetail)
async def get_template_version(
    version_id: int,
    session: AsyncSession = Depends(get_session),
) -> TemplateVersionDetail:
    stmt = select(TemplateVersion).where(TemplateVersion.id == version_id)
    result = await session.execute(stmt)
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template version not found")

    rules = TemplateRulesConfig.model_validate(version.rules_json)
    return TemplateVersionDetail(
        id=version.id,
        template_id=version.template_id,
        version_number=version.version_number,
        created_at=version.created_at,
        created_by_admin_id=version.created_by_admin_id,
        rules=rules,
    )


@router.put("/template_versions/{version_id}", response_model=TemplateVersionDetail)
async def update_template_version(
    version_id: int,
    payload: TemplateVersionUpdate,
    session: AsyncSession = Depends(get_session),
) -> TemplateVersionDetail:
    stmt = select(TemplateVersion).where(TemplateVersion.id == version_id)
    result = await session.execute(stmt)
    version = result.scalar_one_or_none()
    if version is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Template version not found")

    rules_dict = payload.rules.model_dump(mode="json")
    version.rules_json = rules_dict
    await session.flush()

    return TemplateVersionDetail(
        id=version.id,
        template_id=version.template_id,
        version_number=version.version_number,
        created_at=version.created_at,
        created_by_admin_id=version.created_by_admin_id,
        rules=payload.rules,
    )


@router.get("/bot_content", response_model=list[BotContentItem])
async def list_bot_content(
    session: AsyncSession = Depends(get_session),
) -> list[BotContentItem]:
    stmt = select(BotContent).order_by(BotContent.key)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        BotContentItem(
            id=row.id,
            key=row.key,
            value=row.value,
            extra=row.extra,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/bot_content/{content_id}", response_model=BotContentItem)
async def get_bot_content(
    content_id: int,
    session: AsyncSession = Depends(get_session),
) -> BotContentItem:
    stmt = select(BotContent).where(BotContent.id == content_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BotContent not found")
    return BotContentItem(
        id=row.id,
        key=row.key,
        value=row.value,
        extra=row.extra,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.post("/bot_content", response_model=BotContentItem, status_code=status.HTTP_201_CREATED)
async def create_bot_content(
    payload: BotContentCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> BotContentItem:
    row = BotContent(
        key=payload.key,
        value=payload.value,
        extra=payload.extra,
    )
    session.add(row)
    await session.flush()

    audit = AuditLog(
        admin_user_id=None,
        action="bot_content.create",
        entity_type="bot_content",
        entity_id=row.id,
        diff_json={
            "before": None,
            "after": {
                "key": row.key,
                "value": row.value,
                "extra": row.extra,
            },
        },
    )
    session.add(audit)
    await session.flush()

    return BotContentItem(
        id=row.id,
        key=row.key,
        value=row.value,
        extra=row.extra,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.put("/bot_content/{content_id}", response_model=BotContentItem)
async def update_bot_content(
    content_id: int,
    payload: BotContentCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> BotContentItem:
    stmt = select(BotContent).where(BotContent.id == content_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BotContent not found")

    before = {
        "key": row.key,
        "value": row.value,
        "extra": row.extra,
    }

    row.key = payload.key
    row.value = payload.value
    row.extra = payload.extra
    await session.flush()

    audit = AuditLog(
        admin_user_id=None,
        action="bot_content.update",
        entity_type="bot_content",
        entity_id=row.id,
        diff_json={
            "before": before,
            "after": {
                "key": row.key,
                "value": row.value,
                "extra": row.extra,
            },
        },
    )
    session.add(audit)
    await session.flush()

    return BotContentItem(
        id=row.id,
        key=row.key,
        value=row.value,
        extra=row.extra,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.delete("/bot_content/{content_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bot_content(
    content_id: int,
    session: AsyncSession = Depends(get_session),
) -> None:
    stmt = select(BotContent).where(BotContent.id == content_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="BotContent not found")

    before = {
        "key": row.key,
        "value": row.value,
        "extra": row.extra,
    }

    await session.delete(row)
    await session.flush()

    audit = AuditLog(
        admin_user_id=None,
        action="bot_content.delete",
        entity_type="bot_content",
        entity_id=content_id,
        diff_json={
            "before": before,
            "after": None,
        },
    )
    session.add(audit)
    await session.flush()


@router.get("/audit_logs", response_model=list[AuditLogItem])
async def list_audit_logs(
    session: AsyncSession = Depends(get_session),
) -> list[AuditLogItem]:
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        AuditLogItem(
            id=row.id,
            admin_user_id=row.admin_user_id,
            action=row.action,
            entity_type=row.entity_type,
            entity_id=row.entity_id,
            diff_json=row.diff_json,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/products", response_model=list[ProductItem])
async def list_products_admin(
    session: AsyncSession = Depends(get_session),
) -> list[ProductItem]:
    stmt = select(Product).order_by(Product.name)
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        ProductItem(
            id=row.id,
            name=row.name,
            price=float(row.price),
            currency=row.currency,
            credits_amount=row.credits_amount,
            active=row.active,
            description=row.description,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.post("/products", response_model=ProductItem, status_code=status.HTTP_201_CREATED)
async def create_product_admin(
    payload: ProductCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProductItem:
    row = Product(
        name=payload.name,
        price=payload.price,
        currency=payload.currency,
        credits_amount=payload.credits_amount,
        active=payload.active,
        description=payload.description,
    )
    session.add(row)
    await session.flush()
    return ProductItem(
        id=row.id,
        name=row.name,
        price=float(row.price),
        currency=row.currency,
        credits_amount=row.credits_amount,
        active=row.active,
        description=row.description,
        created_at=row.created_at,
    )


@router.put("/products/{product_id}", response_model=ProductItem)
async def update_product_admin(
    product_id: int,
    payload: ProductCreateUpdate,
    session: AsyncSession = Depends(get_session),
) -> ProductItem:
    stmt = select(Product).where(Product.id == product_id)
    result = await session.execute(stmt)
    row = result.scalar_one_or_none()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")

    row.name = payload.name
    row.price = payload.price
    row.currency = payload.currency
    row.credits_amount = payload.credits_amount
    row.active = payload.active
    row.description = payload.description
    await session.flush()

    return ProductItem(
        id=row.id,
        name=row.name,
        price=float(row.price),
        currency=row.currency,
        credits_amount=row.credits_amount,
        active=row.active,
        description=row.description,
        created_at=row.created_at,
    )


@router.get("/orders", response_model=list[OrderItemAdmin])
async def list_orders_admin(
    session: AsyncSession = Depends(get_session),
) -> list[OrderItemAdmin]:
    stmt = select(Order).order_by(Order.created_at.desc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        OrderItemAdmin(
            id=row.id,
            user_id=row.user_id,
            product_id=row.product_id,
            status=row.status,
            amount=float(row.amount),
            created_at=row.created_at,
            paid_at=row.paid_at,
        )
        for row in rows
    ]


@router.get("/payments_prodamus", response_model=list[ProdamusPaymentItem])
async def list_payments_prodamus_admin(
    session: AsyncSession = Depends(get_session),
) -> list[ProdamusPaymentItem]:
    stmt = select(ProdamusPayment).order_by(ProdamusPayment.created_at.desc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        ProdamusPaymentItem(
            id=row.id,
            order_id=row.order_id,
            prodamus_invoice_id=row.prodamus_invoice_id,
            status=row.status,
            raw_payload=row.raw_payload,
            created_at=row.created_at,
        )
        for row in rows
    ]


@router.get("/checks", response_model=list[CheckItemAdmin])
async def list_checks_admin(
    session: AsyncSession = Depends(get_session),
) -> list[CheckItemAdmin]:
    stmt = select(Check).order_by(Check.created_at.desc())
    result = await session.execute(stmt)
    rows = result.scalars().all()
    return [
        CheckItemAdmin(
            id=row.id,
            user_id=row.user_id,
            template_version_id=row.template_version_id,
            gost_id=row.gost_id,
            status=row.status,
            created_at=row.created_at,
            finished_at=row.finished_at,
            input_file_id=row.input_file_id,
            result_report_id=row.result_report_id,
            output_file_id=row.output_file_id,
        )
        for row in rows
    ]

