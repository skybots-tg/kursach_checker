from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Sequence

import jwt
from fastapi import APIRouter, Depends, HTTPException, Request, Response, UploadFile, File as FastAPIFile, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import get_settings
from backend.db import get_session
from backend.db.models_domain import Check, File, Gost, Template, University
from backend.db.models_users import Order, ProdamusPayment, User
from backend.rules_engine.findings import CheckReport
from backend.schemas.miniapp import (
    CheckDetailResponse,
    CheckItem,
    CheckStartRequest,
    GostItem,
    MeResponse,
    OrderItem,
    PaymentCreateRequest,
    PaymentCreateResponse,
    ProductItem,
    SessionResponse,
    TelegramAuthRequest,
    TemplateItem,
    UniversityItem,
    FileUploadResponse,
)
from backend.services.checks import ChecksService
from backend.services.payments import PaymentsService
from backend.services.users import UserService
from backend.storage.files import FileStorage
from backend.integrations.telegram_miniapp import verify_init_data
from arq.connections import create_pool, RedisSettings
from backend.integrations.telegram_bot import send_text_message



router = APIRouter(prefix="/api/miniapp", tags=["miniapp"])

security = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Извлекает текущего пользователя из JWT‑токена.

    В тестовом режиме (miniapp_test_mode=True) при отсутствии токена
    используется/создаётся тестовый пользователь.
    """
    settings = get_settings()

    # Тестовый режим: позволяем работать без JWT.
    if credentials is None and settings.miniapp_test_mode:
        user_service = UserService(session)
        telegram_id = settings.miniapp_test_user_telegram_id or 999_999_999
        user = await user_service.get_or_create_telegram_user(
            telegram_id=telegram_id,
            first_name="Test",
            username="test_user",
        )
        return user

    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.PyJWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    user_id = payload.get("sub")
    if not isinstance(user_id, int):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    stmt = select(User).where(User.id == user_id)
    result = await session.execute(stmt)
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")
    return user


@router.post("/auth/telegram", response_model=SessionResponse)
async def auth_telegram(
    payload: TelegramAuthRequest,
    session: AsyncSession = Depends(get_session),
) -> SessionResponse:
    """
    Авторизация Mini App по initData от Telegram.

    1) Валидируем подпись initData.
    2) Извлекаем данные пользователя.
    3) Создаём/обновляем пользователя в БД.
    4) Возвращаем JWT‑сессию.
    """
    settings = get_settings()
    data = verify_init_data(payload.init_data, bot_token=settings.telegram_bot_token)

    user_raw = data.get("user")
    if not user_raw:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="user not found in initData")

    try:
        user_data = json.loads(user_raw)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid user payload")

    telegram_id = user_data.get("id")
    if not isinstance(telegram_id, int):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid telegram id")

    first_name = user_data.get("first_name")
    username = user_data.get("username")

    user_service = UserService(session)
    user = await user_service.get_or_create_telegram_user(
        telegram_id=telegram_id,
        first_name=first_name,
        username=username,
    )

    now = datetime.utcnow()
    expires_delta = timedelta(seconds=settings.jwt_ttl_seconds)
    payload_jwt = {
        "sub": user.id,
        "telegram_id": telegram_id,
        "exp": now + expires_delta,
        "iat": now,
    }
    token = jwt.encode(payload_jwt, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return SessionResponse(
        access_token=token,
        expires_in=settings.jwt_ttl_seconds,
    )


@router.post("/auth/test", response_model=SessionResponse)
async def auth_test(
    session: AsyncSession = Depends(get_session),
) -> SessionResponse:
    """
    Тестовая авторизация без Telegram.

    Включается флагом miniapp_test_mode=True в .env.
    Создаёт/использует тестового пользователя и возвращает JWT, как /auth/telegram.
    """
    settings = get_settings()
    if not settings.miniapp_test_mode:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Test auth disabled")

    user_service = UserService(session)
    telegram_id = settings.miniapp_test_user_telegram_id or 999_999_999
    user = await user_service.get_or_create_telegram_user(
        telegram_id=telegram_id,
        first_name="Test",
        username="test_user",
    )

    now = datetime.utcnow()
    expires_delta = timedelta(seconds=settings.jwt_ttl_seconds)
    payload_jwt = {
        "sub": user.id,
        "telegram_id": telegram_id,
        "exp": now + expires_delta,
        "iat": now,
    }
    token = jwt.encode(payload_jwt, settings.jwt_secret, algorithm=settings.jwt_algorithm)

    return SessionResponse(
        access_token=token,
        expires_in=settings.jwt_ttl_seconds,
    )


@router.get("/me", response_model=MeResponse)
async def get_me(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> MeResponse:
    """Профиль пользователя + баланс кредитов для Mini App."""
    user_service = UserService(session)
    credits = await user_service.get_credits_balance(current_user.id)
    return MeResponse(
        id=current_user.id,
        telegram_id=current_user.telegram_id,
        first_name=current_user.first_name,
        username=current_user.username,
        credits_available=credits,
    )


@router.get("/universities", response_model=list[UniversityItem])
async def list_universities(session: AsyncSession = Depends(get_session)) -> list[UniversityItem]:
    stmt = select(University).where(University.active.is_(True)).order_by(University.priority, University.name)
    result = await session.execute(stmt)
    rows: Sequence[University] = result.scalars().all()
    return [
        UniversityItem(
            id=u.id,
            name=u.name,
            active=u.active,
        )
        for u in rows
    ]


@router.get("/gosts", response_model=list[GostItem])
async def list_gosts(session: AsyncSession = Depends(get_session)) -> list[GostItem]:
    stmt = select(Gost).where(Gost.active.is_(True)).order_by(Gost.name)
    result = await session.execute(stmt)
    rows: Sequence[Gost] = result.scalars().all()
    return [
        GostItem(
            id=g.id,
            name=g.name,
            description=g.description,
            active=g.active,
        )
        for g in rows
    ]


@router.get("/templates", response_model=list[TemplateItem])
async def list_templates(
    university_id: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> list[TemplateItem]:
    stmt = select(Template).where(Template.active.is_(True), Template.status == "published")
    if university_id is not None:
        stmt = stmt.where(Template.university_id == university_id)
    stmt = stmt.order_by(Template.name)

    result = await session.execute(stmt)
    rows: Sequence[Template] = result.scalars().all()
    return [
        TemplateItem(
            id=t.id,
            name=t.name,
            type_work=t.type_work,
            year=t.year,
        )
        for t in rows
    ]


@router.post("/payments/create", response_model=PaymentCreateResponse)
async def create_payment(
    payload: PaymentCreateRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> PaymentCreateResponse:
    """
    Создаёт заказ и возвращает URL для оплаты через Prodamus.

    Реальная интеграция с Prodamus будет добавлена отдельно; сейчас формируется
    предсказуемый URL‑заглушка, который можно заменить на реальный платёжный линк.
    """
    settings = get_settings()
    payments_service = PaymentsService(session)
    order = await payments_service.create_order(user_id=current_user.id, product_id=payload.product_id)

    payment_url = f"{settings.prodamus_payment_base_url}?order_id={order.id}"
    return PaymentCreateResponse(payment_url=payment_url, order_id=order.id)


@router.get("/orders", response_model=list[OrderItem])
async def list_orders(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[OrderItem]:
    stmt = (
        select(Order)
        .where(Order.user_id == current_user.id)
        .order_by(Order.created_at.desc())
    )
    result = await session.execute(stmt)
    rows: Sequence[Order] = result.scalars().all()
    return [
        OrderItem(
            id=o.id,
            status=o.status,
            amount=float(o.amount),
            created_at=o.created_at,
            paid_at=o.paid_at,
        )
        for o in rows
    ]


@router.get("/products", response_model=list[ProductItem])
async def list_products(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[ProductItem]:
    """
    Список активных продуктов/тарифов для Mini App.
    """
    payments_service = PaymentsService(session)
    products = await payments_service.get_active_products()
    return [
        ProductItem(
            id=p.id,
            name=p.name,
            price=float(p.price),
            currency=p.currency,
            credits_amount=p.credits_amount,
            description=p.description,
        )
        for p in products
    ]


@router.post("/checks/start", response_model=CheckItem)
async def start_check(
    payload: CheckStartRequest,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CheckItem:
    """
    Запуск проверки документа.

    1) Списываем 1 кредит (если нет — 400).
    2) Создаём запись Check со статусом queued.
    3) (Будет) ставим задачу в очередь воркера.
    """
    user_service = UserService(session)
    has_credit = await user_service.consume_credit(current_user.id)
    if not has_credit:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Not enough credits")

    checks_service = ChecksService(session)
    check = await checks_service.create_check(
        user_id=current_user.id,
        template_version_id=payload.template_version_id,
        gost_id=payload.gost_id,
        input_file_id=payload.file_id,
    )

    # Ставим задачу в очередь arq‑воркера.
    settings = get_settings()
    redis = await create_pool(RedisSettings.from_dsn(settings.redis_dsn))
    await redis.enqueue_job("check_runner", check.id)

    return CheckItem(
        id=check.id,
        status=check.status,
        template_version_id=check.template_version_id,
        gost_id=check.gost_id,
        created_at=check.created_at,
        finished_at=check.finished_at,
    )


@router.post("/files/upload", response_model=FileUploadResponse)
async def upload_file(
    upload: UploadFile = FastAPIFile(...),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> FileUploadResponse:
    """
    Загрузка входного файла для последующей проверки.

    Сейчас поддерживаются только DOC/DOCX, базовая валидация расширения и размера.
    Конкретные ограничения по размеру/форматам могут дополнительно настраиваться
    через шаблоны (input.allowed_file_extensions).
    """
    filename = upload.filename or "document"
    ext = filename.rsplit(".", 1)[-1].lower()
    if ext not in {"doc", "docx"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only DOC/DOCX files are allowed",
        )

    content = await upload.read()
    if not content:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Empty file")

    # Простейшее ограничение размера: до 20 МБ.
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File is too large",
        )

    storage = FileStorage(session)
    mime = upload.content_type or "application/octet-stream"
    saved = await storage.save_bytes(content, original_name=filename, mime=mime)

    return FileUploadResponse(
        file_id=saved.id,
        original_name=saved.original_name,
        mime=saved.mime,
        size=saved.size,
    )


@router.get("/checks", response_model=list[CheckItem])
async def list_checks(
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> list[CheckItem]:
    stmt = (
        select(Check)
        .where(Check.user_id == current_user.id)
        .order_by(Check.created_at.desc())
    )
    result = await session.execute(stmt)
    rows: Sequence[Check] = result.scalars().all()
    return [
        CheckItem(
            id=c.id,
            status=c.status,
            template_version_id=c.template_version_id,
            gost_id=c.gost_id,
            created_at=c.created_at,
            finished_at=c.finished_at,
        )
        for c in rows
    ]


@router.get("/checks/{check_id}", response_model=CheckDetailResponse)
async def get_check_detail(
    check_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> CheckDetailResponse:
    stmt = select(Check).where(Check.id == check_id, Check.user_id == current_user.id)
    result = await session.execute(stmt)
    check = result.scalar_one_or_none()
    if check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Check not found")

    report_data: dict[str, Any] | None = None
    if check.result_report_id is not None:
        file_stmt = select(File).where(File.id == check.result_report_id)
        file_result = await session.execute(file_stmt)
        report_file = file_result.scalar_one_or_none()
        if report_file is not None:
            storage = FileStorage(session)
            raw = storage.open_file(report_file)
            try:
                report_dict = json.loads(raw.decode("utf-8"))
                # Валидация через CheckReport, но наружу отдаём как dict для гибкости фронта.
                _ = CheckReport.model_validate(report_dict)
                report_data = report_dict
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError):
                report_data = None

    return CheckDetailResponse(
        id=check.id,
        status=check.status,
        report=report_data,
        output_file_id=check.output_file_id,
    )


@router.get("/demo/check", response_model=CheckDetailResponse)
async def get_demo_check() -> CheckDetailResponse:
    """
    Демо‑проверка до оплаты.

    Возвращает заранее сохранённый JSON‑отчёт (формат CheckReport),
    который используется Mini App для экрана демо с тем же UI, что и реальные проверки.
    """
    settings = get_settings()
    if not settings.demo_report_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Demo report not configured")

    demo_path = Path(settings.demo_report_path)
    if not demo_path.is_file():
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Demo report file not found")

    try:
        raw = demo_path.read_text("utf-8")
        data = json.loads(raw)
        # Валидация против схемы CheckReport, чтобы демо всегда оставалось консистентным.
        _ = CheckReport.model_validate(data)
    except (OSError, json.JSONDecodeError, ValueError):
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Demo report is invalid")

    return CheckDetailResponse(
        id=0,
        status="demo",
        report=data,
        output_file_id=None,
    )


@router.get("/files/{file_id}/download")
async def download_file(
    file_id: int,
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
) -> Response:
    """
    Скачивание входного/выходного файла или отчёта для своих проверок.
    """
    # Проверяем, что файл принадлежит какому‑то чек‑записи текущего пользователя.
    stmt_checks = select(Check).where(
        Check.user_id == current_user.id,
        (Check.input_file_id == file_id)
        | (Check.result_report_id == file_id)
        | (Check.output_file_id == file_id),
    )
    result_checks = await session.execute(stmt_checks)
    check = result_checks.scalar_one_or_none()
    if check is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    stmt_file = select(File).where(File.id == file_id)
    result_file = await session.execute(stmt_file)
    file = result_file.scalar_one_or_none()
    if file is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")

    storage = FileStorage(session)
    content = storage.open_file(file)

    headers = {
        "Content-Disposition": f'attachment; filename="{file.original_name}"',
    }
    return Response(content=content, media_type=file.mime, headers=headers)


@router.post("/payments/webhook/prodamus")
async def prodamus_webhook(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> dict[str, str]:
    """
    Обработка webhook от Prodamus.

    Формат webhook зависит от настроек магазина, поэтому здесь реализована
    минимальная идемпотентная обработка по invoice_id/order_id/status.
    """
    payload: dict[str, Any] = await request.json()

    invoice_id = str(payload.get("invoice_id") or payload.get("id") or "")
    order_id_raw = payload.get("order_id") or payload.get("order_num")
    status_str = str(payload.get("status") or payload.get("state") or "").lower()

    if not invoice_id or order_id_raw is None:
        # Непонятный webhook — просто подтверждаем получение.
        return {"status": "ignored"}

    try:
        order_id = int(order_id_raw)
    except (TypeError, ValueError):
        return {"status": "ignored"}

    # Идемпотентный апсерт платежа.
    stmt_payment = select(ProdamusPayment).where(ProdamusPayment.prodamus_invoice_id == invoice_id)
    result_payment = await session.execute(stmt_payment)
    payment = result_payment.scalar_one_or_none()

    if payment is None:
        payment = ProdamusPayment(
            order_id=order_id,
            prodamus_invoice_id=invoice_id,
            status=status_str or "unknown",
            raw_payload=payload,
        )
        session.add(payment)
        await session.flush()
    else:
        payment.status = status_str or payment.status
        payment.raw_payload = payload
        await session.flush()

    # Если оплата успешна — отмечаем заказ оплаченным и начисляем кредиты.
    if status_str in {"paid", "success", "successfully"}:
        stmt_order = select(Order).where(Order.id == order_id)
        result_order = await session.execute(stmt_order)
        order = result_order.scalar_one_or_none()
        if order is not None:
            payments_service = PaymentsService(session)
            credits_amount = order.product.credits_amount  # type: ignore[attr-defined]
            await payments_service.mark_payment_paid(order=order, payment=payment, credits_amount=credits_amount)

            # Постараемся уведомить пользователя в Telegram о зачислении кредитов.
            # Здесь же можно получить актуальный баланс, если это потребуется в тексте.
            user_service = UserService(session)
            credits_balance = await user_service.get_credits_balance(order.user_id)

            stmt_user = select(User).where(User.id == order.user_id)
            result_user = await session.execute(stmt_user)
            user = result_user.scalar_one_or_none()
            if user and user.telegram_id:
                await send_text_message(
                    telegram_id=user.telegram_id,
                    text=(
                        "💳 Оплата успешно получена.\n\n"
                        f"Вам начислено {credits_amount} кредит(ов). "
                        f"Сейчас доступно проверок: {credits_balance}.\n\n"
                        "Откройте Mini App через бота, чтобы загрузить документ на проверку."
                    ),
                )

    return {"status": "ok"}

