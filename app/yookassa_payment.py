import requests
import uuid

YOOKASSA_SHOP_ID = "1035013"
YOOKASSA_SECRET_KEY = "test_LvDIvXY-BYCeyqJc1zuhOt1QKcami3BHnm5JdrGkGGY"


async def create_payment(amount, currency="RUB", description="Оплата полной версии", metadata=None):
    """
    Создает платеж через Юкассу.

    :param amount: Сумма оплаты.
    :param currency: Валюта (по умолчанию RUB).
    :param description: Описание платежа.
    :param metadata: Метаданные (например, user_id).
    :return: Ответ от API Юкассы.
    """
    url = "https://api.yookassa.ru/v3/payments"
    headers = {
        "Idempotence-Key": str(uuid.uuid4()),  # Уникальный ключ для идемпотентности
        "Content-Type": "application/json",
    }
    auth = (YOOKASSA_SHOP_ID, YOOKASSA_SECRET_KEY)
    payload = {
        "amount": {
            "value": str(amount),  # Сумма оплаты
            "currency": currency,  # Валюта
        },
        "confirmation": {
            "type": "redirect",
            "return_url": "https://t.me/smartcookbookbot",  # URL для возврата после оплаты
        },
        "capture": True,  # Автоматическое подтверждение платежа
        "description": description,  # Описание платежа
    }

    # Добавляем метаданные, если они переданы
    if metadata:
        payload["metadata"] = metadata

    response = requests.post(url, json=payload, headers=headers, auth=auth)
    return response.json()