from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import settings_kb, confirm_kb, back_kb
from db import db
from utils.device import log_action
from utils.i18n import t

router = Router()

@router.callback_query(F.data == "menu_settings")
async def menu_settings(call: CallbackQuery, device_id: str, lang: str):
    set_row = await db.select_one("settings", "*", {"device_id": device_id})
    await call.message.edit_text(f"⚙️ {t('settings', lang)}", reply_markup=settings_kb(set_row or {}, lang))

@router.callback_query(F.data == "set_lang")
async def toggle_lang(call: CallbackQuery, device_id: str, lang: str):
    new_lang = "en" if lang == "ua" else "ua"
    await db.update("settings", {"language": new_lang}, {"device_id": device_id})
    set_row = await db.select_one("settings", "*", {"device_id": device_id})
    await call.message.edit_text(f"⚙️ {t('settings', new_lang)}", reply_markup=settings_kb(set_row or {}, new_lang))
    await call.answer(t('lang_updated', new_lang))

@router.callback_query(F.data == "set_notif")
async def toggle_notif(call: CallbackQuery, device_id: str, lang: str):
    rows = await db.select("settings", "notify_on_command", {"device_id": device_id})
    if rows:
        current = rows[0].get("notify_on_command", False)
        await db.update("settings", {"notify_on_command": not current}, {"device_id": device_id})
    set_row = await db.select_one("settings", "*", {"device_id": device_id})
    await call.message.edit_reply_markup(reply_markup=settings_kb(set_row or {}, lang))
    await call.answer(t('success', lang))

@router.callback_query(F.data == "set_qual")
async def toggle_quality(call: CallbackQuery, device_id: str, lang: str):
    rows = await db.select("settings", "screenshot_quality", {"device_id": device_id})
    if rows:
        current = rows[0].get("screenshot_quality", "high")
        new_qual = "low" if current == "high" else "high"
        await db.update("settings", {"screenshot_quality": new_qual}, {"device_id": device_id})
    set_row = await db.select_one("settings", "*", {"device_id": device_id})
    await call.message.edit_reply_markup(reply_markup=settings_kb(set_row or {}, lang))
    await call.answer(f"{t('success', lang)}: {set_row.get('screenshot_quality')}")

@router.callback_query(F.data == "set_online_notif")
async def toggle_online_notif(call: CallbackQuery, device_id: str, lang: str):
    rows = await db.select("settings", "notify_online", {"device_id": device_id})
    if rows:
        current = rows[0].get("notify_online", True)
        await db.update("settings", {"notify_online": not current}, {"device_id": device_id})
    set_row = await db.select_one("settings", "*", {"device_id": device_id})
    await call.message.edit_reply_markup(reply_markup=settings_kb(set_row or {}, lang))
    await call.answer(t('success', lang))

@router.callback_query(F.data == "disconnect_pc")
async def disconnect_pc(call: CallbackQuery, lang: str):
    await call.message.edit_text(t('confirm', lang), reply_markup=confirm_kb("disc", lang))

@router.callback_query(F.data == "disc_yes")
async def do_disconnect(call: CallbackQuery, device_id: str, lang: str):
    await db.update("connections", {"is_active": False}, {"device_id": device_id, "user_id": call.from_user.id})
    await log_action(device_id, call.from_user.id, call.from_user.username, "Disconnected PC")
    await call.message.edit_text(t('success', lang))
