from aiogram import BaseMiddleware
from db import db
from keyboards.inline import not_connected_kb


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id

        # Перевіряємо чи юзер підключений до якогось ПК
        rows = await db.select("connections", "device_id", {"user_id": user_id, "is_active": True})
        is_connected = False
        device_id = None

        if rows:
            is_connected = True
            device_id = rows[0]["device_id"]

        data['is_connected'] = is_connected
        data['device_id'] = device_id

        # Винятки для /start та кнопок підключення
        if getattr(event, 'text', '').startswith('/start') or getattr(event, 'data', '') in ['connect_info', 'enter_hash']:
            return await handler(event, data)

        if not is_connected:
            if hasattr(event, 'message'):
                await event.message.answer("Ваш акаунт не підключено до жодного ПК.", reply_markup=not_connected_kb())
            else:
                await event.message.edit_text("Ваш акаунт не підключено до жодного ПК.", reply_markup=not_connected_kb())
            return

        return await handler(event, data)
