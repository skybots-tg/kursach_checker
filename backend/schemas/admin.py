from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from backend.rules_engine.schemas import TemplateRulesConfig


class UniversityItem(BaseModel):
    id: int
    name: str
    active: bool
    description: str | None
    priority: int


class UniversityCreateUpdate(BaseModel):
    name: str
    active: bool = True
    description: str | None = None
    priority: int = 100


class GostItem(BaseModel):
    id: int
    name: str
    description: str | None
    active: bool
    type: str | None
    year: int | None


class GostCreateUpdate(BaseModel):
    name: str
    description: str | None = None
    active: bool = True
    type: str | None = None
    year: int | None = None


class TemplateItem(BaseModel):
    id: int
    university_id: int
    name: str
    type_work: str
    year: int | None
    status: str
    active: bool


class TemplateCreateUpdate(BaseModel):
    university_id: int
    name: str
    type_work: str
    year: int | None = None
    status: str = "draft"
    active: bool = True


class TemplateVersionItem(BaseModel):
    id: int
    template_id: int
    version_number: int
    created_at: datetime
    created_by_admin_id: int | None


class TemplateVersionDetail(BaseModel):
    id: int
    template_id: int
    version_number: int
    created_at: datetime
    created_by_admin_id: int | None
    rules: TemplateRulesConfig


class TemplateVersionCreate(BaseModel):
    rules: TemplateRulesConfig


class TemplateVersionUpdate(BaseModel):
    rules: TemplateRulesConfig


class BotContentItem(BaseModel):
    id: int
    key: str
    value: str
    extra: dict[str, Any] | None
    created_at: datetime
    updated_at: datetime


class BotContentCreateUpdate(BaseModel):
    key: str
    value: str
    extra: dict[str, Any] | None = None


class AuditLogItem(BaseModel):
    id: int
    admin_user_id: int | None
    action: str
    entity_type: str | None
    entity_id: int | None
    diff_json: dict[str, Any] | None
    created_at: datetime


class ProductItem(BaseModel):
    id: int
    name: str
    price: float
    currency: str
    credits_amount: int
    active: bool
    description: str | None
    created_at: datetime


class ProductCreateUpdate(BaseModel):
    name: str
    price: float
    currency: str = "RUB"
    credits_amount: int = 1
    active: bool = True
    description: str | None = None


class OrderItemAdmin(BaseModel):
    id: int
    user_id: int
    product_id: int
    status: str
    amount: float
    created_at: datetime
    paid_at: datetime | None


class ProdamusPaymentItem(BaseModel):
    id: int
    order_id: int
    prodamus_invoice_id: str
    status: str
    raw_payload: dict[str, Any]
    created_at: datetime


class CheckItemAdmin(BaseModel):
    id: int
    user_id: int
    template_version_id: int
    gost_id: int | None
    status: str
    created_at: datetime
    finished_at: datetime | None
    input_file_id: int
    result_report_id: int | None
    output_file_id: int | None
