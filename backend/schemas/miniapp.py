from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel


class TelegramAuthRequest(BaseModel):
    """initData от Telegram Mini App."""

    init_data: str


class SessionResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class MeResponse(BaseModel):
    id: int
    telegram_id: int
    first_name: str | None
    username: str | None
    credits_available: int


class UniversityItem(BaseModel):
    id: int
    name: str
    active: bool


class GostItem(BaseModel):
    id: int
    name: str
    description: str | None
    active: bool


class TemplateItem(BaseModel):
    id: int
    name: str
    type_work: str
    year: int | None


class PaymentCreateRequest(BaseModel):
    product_id: int


class PaymentCreateResponse(BaseModel):
    payment_url: str
    order_id: int


class OrderItem(BaseModel):
    id: int
    status: str
    amount: float
    created_at: datetime
    paid_at: datetime | None


class ProductItem(BaseModel):
    id: int
    name: str
    price: float
    currency: str
    credits_amount: int
    description: str | None


class CheckStartRequest(BaseModel):
    template_version_id: int
    gost_id: int | None = None
    file_id: int


class CheckItem(BaseModel):
    id: int
    status: str
    template_version_id: int
    gost_id: int | None
    created_at: datetime
    finished_at: datetime | None


class CheckDetailResponse(BaseModel):
    id: int
    status: str
    report: dict[str, Any] | None
    output_file_id: int | None


class FileUploadResponse(BaseModel):
    """Результат загрузки файла в Mini App."""

    file_id: int
    original_name: str
    mime: str
    size: int




