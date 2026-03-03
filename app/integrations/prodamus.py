from urllib.parse import urlencode

from app.core.config import settings


def build_payment_url(order_id: int, amount: float, customer_id: int) -> str:
    base_url = "https://payform.prodamus.ru"
    params = {
        "order_id": order_id,
        "do": "link",
        "sum": f"{amount:.2f}",
        "customer_id": str(customer_id),
        "shop_id": settings.prodamus_shop_id,
    }
    return f"{base_url}/?{urlencode(params)}"

