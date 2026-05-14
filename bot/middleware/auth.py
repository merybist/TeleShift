from aiogram import BaseMiddleware
from db import db
from keyboards.inline import not_connected_kb


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id

        # Check if user is connected to any PC
        rows = await db.select("connections", "device_id", {"user_id": user_id, "is_active": True})
        is_connected = False
        device_id = None

        if rows:
            is_connected = True
            device_id = rows[0]["device_id"]

        data['is_connected'] = is_connected
        data['device_id'] = device_id

        # Exceptions for /start and connection buttons
        if getattr(event, 'text', '').startswith('/start') or getattr(event, 'data', '') in ['connect_info', 'enter_hash']:
            return await handler(event, data)

        if not is_connected:
            if hasattr(event, 'message'):
                await event.message.answer("Your account is not connected to any PC.", reply_markup=not_connected_kb())
            else:
                await event.message.edit_text("Your account is not connected to any PC.", reply_markup=not_connected_kb())
            return

        return await handler(event, data)
