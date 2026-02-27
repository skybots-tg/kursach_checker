from __future__ import annotations

"""
Валидация initData для Telegram Mini App.

Алгоритм описан в документации Telegram:
https://core.telegram.org/bots/webapps#validating-data-received-via-the-web-app
"""

import hashlib
import hmac
from urllib.parse import parse_qsl


def verify_init_data(init_data: str, bot_token: str) -> dict[str, str]:
    """
    Проверяет подпись initData и возвращает разобранные параметры.

    Возбуждает ValueError при неверной подписи.
    """
    # Парсим query‑строку в пары ключ‑значение.
    data_pairs = dict(parse_qsl(init_data, keep_blank_values=True))

    received_hash = data_pairs.pop("hash", None)
    if not received_hash:
        raise ValueError("hash is missing in initData")

    # Сортируем оставшиеся ключи по алфавиту и собираем строку "key=value" через \n.
    data_check_string = "\n".join(f"{k}={data_pairs[k]}" for k in sorted(data_pairs.keys()))

    # Секретный ключ: HMAC-SHA256 от строки "WebAppData" с ключом bot_token.
    secret_key = hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()
    calculated_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(calculated_hash, received_hash):
        raise ValueError("invalid initData hash")

    return data_pairs







