import hashlib
import hmac
import json
from urllib.parse import parse_qs, urlencode

from app.core.config import settings


def _normalize_value(value):
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, (int, float, str)):
        return str(value)
    if isinstance(value, list):
        return [_normalize_value(v) for v in value]
    if isinstance(value, dict):
        return {k: _normalize_value(value[k]) for k in sorted(value)}
    return str(value)


def canonical_json(data: dict) -> str:
    normalized = _normalize_value(data)
    raw = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
    return raw.replace("/", "\\/")


def build_signature(data: dict, secret_key: str) -> str:
    message = canonical_json(data).encode("utf-8")
    return hmac.new(secret_key.encode("utf-8"), message, hashlib.sha256).hexdigest()


def verify_signature(data: dict, signature: str | None, secret_key: str) -> bool:
    if not signature:
        return False
    expected = build_signature(data, secret_key)
    return hmac.compare_digest(expected, signature)


def extract_payload_and_signature(raw_body: bytes, content_type: str) -> tuple[dict, str | None]:
    if "application/json" in content_type:
        payload = json.loads(raw_body.decode("utf-8") or "{}")
        signature = payload.get("signature")
        return payload, signature

    form = parse_qs(raw_body.decode("utf-8"), keep_blank_values=True)
    payload = {k: (v[0] if len(v) == 1 else v) for k, v in form.items()}
    signature = str(payload.get("signature", "")) or None
    return payload, signature


def build_link_payload(order_id: str, amount: float, product_name: str) -> dict:
    payload = {
        "do": "link",
        "order_id": order_id,
        "order_num": order_id,
        "currency": "rub",
        "products": [
            {
                "name": product_name,
                "price": f"{amount:.2f}",
                "quantity": 1,
            }
        ],
        "urlNotification": f"{settings.app_base_url}/api/payments/webhook/prodamus",
    }
    if settings.prodamus_sys:
        payload["sys"] = settings.prodamus_sys
    return payload


def build_link_request_url(payload: dict) -> str:
    signed_payload = dict(payload)
    signed_payload["signature"] = build_signature(payload, settings.prodamus_secret_key)
    return f"{settings.prodamus_payform_url}?{urlencode(signed_payload, doseq=True)}"
