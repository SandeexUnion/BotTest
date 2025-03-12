from fastapi import FastAPI, Request, HTTPException
import hmac
import hashlib
import json
from aiogram import Bot
from app.database.models import async_session
from app.handlers import update_user_access

app = FastAPI()

YOOKASSA_SECRET_KEY = "test_LvDIvXY-BYCeyqJc1zuhOt1QKcami3BHnm5JdrGkGGY"

@app.post('/yookassa-webhook')
async def yookassa_webhook(request: Request, bot: Bot):
    # Получаем данные из запроса
    data = await request.body()
    signature = request.headers.get('Content-SHA256')

    # Проверяем подпись
    if not verify_signature(data.decode(), signature):
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Обрабатываем уведомление
    event = json.loads(data)
    if event.get("event") == "payment.succeeded":
        payment = event.get("object")
        user_id = payment.get("metadata", {}).get("user_id")
        if user_id:
            # Обновляем данные пользователя
            success = await update_user_access(int(user_id))
            if success:
                # Отправляем уведомление пользователю
                await bot.send_message(user_id, "Оплата прошла успешно! Теперь у вас есть доступ к полной версии.")
                return {"status": "success"}
            else:
                raise HTTPException(status_code=404, detail="User not found")

    return {"status": "ignored"}

def verify_signature(data, signature):
    # Создаем HMAC-подпись
    hmac_digest = hmac.new(
        YOOKASSA_SECRET_KEY.encode(),
        data.encode(),
        hashlib.sha256
    ).hexdigest()
    return hmac_digest == signature