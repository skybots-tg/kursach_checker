import hashlib
import hmac
import json
import logging
from typing import Any
from urllib.parse import urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def _deep_sort(obj: Any) -> Any:
    """Рекурсивная сортировка ключей + приведение значений к строке."""
    if isinstance(obj, dict):
        return {k: _deep_sort(v) for k, v in sorted(obj.items())}
    if isinstance(obj, list):
        return [_deep_sort(item) for item in obj]
    return str(obj)


def create_signature(data: dict, secret_key: str | None = None) -> str:
    """HMAC-SHA256 подпись по алгоритму Prodamus."""
    secret_key = secret_key or settings.prodamus_secret_key
    sorted_data = _deep_sort(data)
    json_str = json.dumps(sorted_data, ensure_ascii=False, separators=(",", ":"))
    json_str = json_str.replace("/", "\\/")
    return hmac.new(
        secret_key.encode("utf-8"),
        json_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(data: dict, signature: str, secret_key: str | None = None) -> bool:
    """Проверка подписи входящего webhook."""
    if not signature:
        return False
    expected = create_signature(data, secret_key)
    return hmac.compare_digest(expected, signature)


def _flatten(obj: Any, prefix: str | None = None) -> list[tuple[str, str]]:
    """Вложенный dict/list → плоские пары в стиле PHP http_build_query."""
    if isinstance(obj, dict):
        items: list[tuple[str, str]] = []
        for key, value in obj.items():
            new_key = key if prefix is None else f"{prefix}[{key}]"
            items.extend(_flatten(value, new_key))
        return items
    if isinstance(obj, list):
        items = []
        for i, value in enumerate(obj):
            items.extend(_flatten(value, f"{prefix}[{i}]"))
        return items
    return [(prefix or "", str(obj))]


async def create_payment_link(
    order_id: str,
    amount: int | float,
    product_name: str = "Оплата заказа",
) -> str | None:
    """Создаёт ссылку на оплату через Prodamus API (do=link)."""
    webhook_url = f"{settings.app_base_url}/api/payments/webhook/prodamus"

    data: dict[str, Any] = {
        "do": "link",
        "type": "json",
        "callbackType": "json",
        "order_id": order_id,
        "products": [
            {
                "name": product_name,
                "price": str(int(amount)) if float(amount) == int(amount) else str(amount),
                "quantity": "1",
            }
        ],
        "urlNotification": webhook_url,
        "payments_limit": "1",
        "currency": "rub",
    }

    data["signature"] = create_signature(data)

    payload = urlencode(_flatten(data), doseq=True, encoding="utf-8")

    async with httpx.AsyncClient(timeout=float(settings.prodamus_timeout_sec)) as client:
        resp = await client.post(
            settings.prodamus_payform_url,
            content=payload,
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=utf-8"},
        )

    text = resp.text.strip()
    if text.startswith("http"):
        return text

    ct = resp.headers.get("content-type", "")
    if "json" in ct:
        body = resp.json()
        return body.get("link") or body.get("payment_link") or body.get("url")

    logger.error("Prodamus error %s: %s", resp.status_code, text[:300])
    return None
