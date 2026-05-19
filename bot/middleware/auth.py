from aiogram import BaseMiddleware
from db import db
from keyboards.inline import not_connected_kb


class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = event.from_user.id

        rows = await db.select("connections", "device_id", {"user_id": user_id, "is_active": True})
        is_connected = False
        device_id = None
        lang = "en"

        if rows:
            is_connected = True
            device_id = rows[0]["device_id"]
            settings = await db.select_one("settings", "language", {"device_id": device_id})
            if settings and settings.get("language"):
                lang = settings["language"]

        data['is_connected'] = is_connected
        data['device_id'] = device_id
        data['lang'] = lang

        if getattr(event, 'text', '').startswith('/start') or getattr(event, 'data', '') in ['connect_info', 'enter_hash']:
            return await handler(event, data)

        if not is_connected:
            from locales import t
            if hasattr(event, 'message'):
                await event.message.answer(t("not_connected", lang), reply_markup=not_connected_kb(lang))
            else:
                await event.message.edit_text(t("not_connected", lang), reply_markup=not_connected_kb(lang))
            return

        return await handler(event, data)
