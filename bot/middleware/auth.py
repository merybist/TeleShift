from aiogram import BaseMiddleware
from db import db

class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id
        rows = await db.select("connections", "device_id", {"user_id": user_id, "is_active": True})
        is_connected = False
        device_id = None
        if rows:
            is_connected = True
            device_id = rows[0]["device_id"]
        data['is_connected'] = is_connected
        data['device_id'] = device_id
        lang = 'ua'
        if device_id:
            set_row = await db.select_one("settings", "language", {"device_id": device_id})
            if set_row: lang = set_row.get("language", "ua")
        data['lang'] = lang

        if getattr(event, 'text', '').startswith('/start') or getattr(event, 'data', '') in ['connect_info', 'enter_hash']:
            return await handler(event, data)
        if not is_connected:
            from keyboards.inline import not_connected_kb
            text = "Your account is not connected to any PC."
            if hasattr(event, 'message'): await event.message.answer(text, reply_markup=not_connected_kb(lang))
            else: await event.message.edit_text(text, reply_markup=not_connected_kb(lang))
            return
        return await handler(event, data)
