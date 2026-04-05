import hashlib
import hmac
import json
import logging
import re
from collections.abc import Mapping
from copy import deepcopy
from typing import Any
from urllib.parse import parse_qsl, urlencode

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def create_signature(data: dict, secret_key: str | None = None) -> str:
    """HMAC-SHA256 подпись — алгоритм совместим с официальной prodamuspy."""
    secret_key = secret_key or settings.prodamus_secret_key
    json_str = json.dumps(data, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
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
    return hmac.compare_digest(expected.lower(), signature.lower())


def parse_form_body(body: str) -> dict:
    """Разбор PHP-style query string (products[0][name]=...) во вложенный dict."""
    payload = dict(parse_qsl(body, keep_blank_values=True))
    return _php2dict(payload)


def _php2dict(array: dict) -> dict:
    dct: dict = {}
    for k, v in array.items():
        m = re.fullmatch(r"([^\[]+)(\[.+\])", k)
        if m:
            idx = [m.group(1)] + list(re.findall(r"\[([^\]]+)\]", m.group(2)))
            subdct = _dict_build(idx, v)
        else:
            subdct = {k: v}
        dct = _dict_merge(dct, subdct)
    return dct


def _dict_build(idx: list, value: Any) -> Any:
    value = deepcopy(value)
    if idx:
        i = idx.pop(0)
        if re.fullmatch(r"[0-9]+", i):
            return [{} for _ in range(int(i))] + [_dict_build(idx, value)]
        return {i: _dict_build(idx, value)}
    return value


def _dict_merge(dct: dict, merge_dct: dict) -> dict:
    dct = deepcopy(dct)
    for k, v in merge_dct.items():
        if not dct.get(k):
            dct[k] = deepcopy(v)
        elif k in dct and type(v) != type(dct[k]):
            raise TypeError(f"Overlapping keys with different types: {type(dct[k])} vs {type(v)}")
        elif isinstance(dct[k], dict) and isinstance(v, Mapping):
            dct[k] = _dict_merge(dct[k], v)
        elif isinstance(v, list):
            for li, lv in enumerate(v):
                if len(dct[k]) <= li:
                    dct[k].append(lv)
                else:
                    dct[k][li] = _dict_merge(dct[k][li], lv)
        else:
            dct[k] = v
    return dct


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
