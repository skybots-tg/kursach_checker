import hashlib
import hmac
import json
import logging
import re
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
    """HMAC-SHA256 подпись по алгоритму Prodamus.

    1. Все значения → строки, ключи рекурсивно сортируются
    2. JSON без пробелов
    3. Слэши ``/`` экранируются как ``\\/``
    """
    key = secret_key or settings.prodamus_secret_key
    sorted_data = _deep_sort(data)
    json_str = json.dumps(sorted_data, ensure_ascii=False, separators=(",", ":"))
    json_str = json_str.replace("/", "\\/")
    return hmac.new(
        key.encode("utf-8"),
        json_str.encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_signature(data: dict, signature: str, secret_key: str | None = None) -> bool:
    """Проверка подписи входящего webhook."""
    if not signature:
        return False
    expected = create_signature(data, secret_key)
    return hmac.compare_digest(expected, signature)


def unflatten_form_data(flat_dict: dict[str, Any]) -> dict[str, Any]:
    """Конвертация плоских form-data ключей (products[0][name]) во вложенный dict."""
    result: dict[str, Any] = {}
    for key, value in flat_dict.items():
        str_value = str(value)
        if "[" in key and key.endswith("]"):
            parts = re.findall(r"([^\[\]]+)", key)
            if len(parts) > 1:
                current = result
                i = 0
                while i < len(parts) - 1:
                    part = parts[i]
                    if i + 1 < len(parts) - 1 and parts[i + 1].isdigit():
                        idx = int(parts[i + 1])
                        if part not in current:
                            current[part] = []
                        arr = current[part]
                        if not isinstance(arr, list):
                            arr = []
                            current[part] = arr
                        while len(arr) <= idx:
                            arr.append({})
                        current = arr[idx]
                        i += 2
                    else:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                        i += 1
                final_key = parts[-1]
                if isinstance(current, dict):
                    current[final_key] = str_value
                else:
                    result[key] = str_value
            else:
                result[key] = str_value
        else:
            result[key] = str_value
    return result


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
    customer_extra: str | None = None,
) -> str | None:
    """Создаёт ссылку на оплату через Prodamus API (do=link)."""
    webhook_url = f"{settings.app_base_url}/api/payments/webhook/prodamus"
    logger.info("Prodamus payment link: order_id=%s, webhook_url=%s", order_id, webhook_url)

    data: dict[str, Any] = {
        "do": "link",
        "type": "json",
        "callbackType": "json",
        "order_id": order_id,
        "customer_extra": customer_extra or f"order-{order_id}",
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
