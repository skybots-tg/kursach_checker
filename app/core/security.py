import hashlib
import hmac
import json
import time
from urllib.parse import parse_qsl

import jwt
from fastapi import HTTPException, status

from app.core.config import settings


def create_access_token(user_id: int) -> str:
    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + settings.jwt_expire_hours * 3600,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_admin_token(admin_id: int, role: str) -> str:
    now = int(time.time())
    payload = {
        "sub": str(admin_id),
        "role": role,
        "iat": now,
        "exp": now + settings.admin_jwt_expire_hours * 3600,
    }
    return jwt.encode(payload, settings.admin_jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> int:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return int(payload["sub"])
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Неверный токен") from exc


def validate_telegram_init_data(init_data: str, bot_token: str) -> dict:
    if not bot_token:
        raise HTTPException(status_code=500, detail="Telegram bot token не настроен")

    pairs = dict(parse_qsl(init_data, keep_blank_values=True))
    received_hash = pairs.pop("hash", None)
    if not received_hash:
        raise HTTPException(status_code=401, detail="Отсутствует hash в initData")

    auth_date_str = pairs.get("auth_date")
    if auth_date_str:
        try:
            auth_ts = int(auth_date_str)
            if time.time() - auth_ts > settings.telegram_auth_max_age_sec:
                raise HTTPException(status_code=401, detail="initData устарел")
        except ValueError:
            raise HTTPException(status_code=401, detail="Некорректный auth_date")

    data_check_string = "\n".join(f"{k}={v}" for k, v in sorted(pairs.items()))
    secret = hmac.new(b"WebAppData", bot_token.encode(), hashlib.sha256).digest()
    calc_hash = hmac.new(secret, data_check_string.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calc_hash, received_hash):
        raise HTTPException(status_code=401, detail="Некорректная подпись Telegram")

    user_raw = pairs.get("user")
    if not user_raw:
        raise HTTPException(status_code=401, detail="В initData нет данных пользователя")

    return json.loads(user_raw)


def validate_prodamus_signature(raw_body: bytes, signature: str | None, secret_key: str) -> bool:
    if not signature or not secret_key:
        return False
    expected = hmac.new(secret_key.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


