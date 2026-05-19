import logging
from datetime import datetime, timezone

from aiogram import Router, F
from aiogram.types import CallbackQuery
from db import db
from locales import t
from keyboards.inline import settings_kb, settings_notif_kb, settings_prefs_kb, confirm_kb, back_kb
from utils.device import log_action, is_device_online

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu_settings")
async def menu_settings(call: CallbackQuery, lang: str = "en"):
    await call.message.edit_text(t("settings_title", lang), reply_markup=settings_kb(lang))


# ── Notifications submenu ──────────────────────────────────────

@router.callback_query(F.data == "settings_notif")
async def settings_notif(call: CallbackQuery, device_id: str, lang: str = "en"):
    rows = await db.select("settings", "*", {"device_id": device_id})
    settings = rows[0] if rows else {}
    await call.message.edit_text(t("notif_title", lang), reply_markup=settings_notif_kb(settings, lang))


@router.callback_query(F.data == "set_notif")
async def toggle_notif(call: CallbackQuery, device_id: str, lang: str = "en"):
    rows = await db.select("settings", "notify_on_command", {"device_id": device_id})
    if rows:
        current = rows[0].get("notify_on_command", False)
        await db.update("settings", {"notify_on_command": not current}, {"device_id": device_id})

    settings_rows = await db.select("settings", "*", {"device_id": device_id})
    settings = settings_rows[0] if settings_rows else {}
    await call.message.edit_text(t("notif_title", lang), reply_markup=settings_notif_kb(settings, lang))
    await call.answer(t("notif_updated", lang))


@router.callback_query(F.data == "set_online_notif")
async def toggle_online_notif(call: CallbackQuery, device_id: str, lang: str = "en"):
    rows = await db.select("settings", "notify_online", {"device_id": device_id})
    if rows:
        current = rows[0].get("notify_online", True)
        await db.update("settings", {"notify_online": not current}, {"device_id": device_id})

    settings_rows = await db.select("settings", "*", {"device_id": device_id})
    settings = settings_rows[0] if settings_rows else {}
    await call.message.edit_text(t("notif_title", lang), reply_markup=settings_notif_kb(settings, lang))
    await call.answer(t("notif_updated", lang))


# ── Preferences submenu ────────────────────────────────────────

@router.callback_query(F.data == "settings_prefs")
async def settings_prefs(call: CallbackQuery, device_id: str, lang: str = "en"):
    rows = await db.select("settings", "*", {"device_id": device_id})
    settings = rows[0] if rows else {}
    await call.message.edit_text(t("prefs_title", lang), reply_markup=settings_prefs_kb(settings, lang))


@router.callback_query(F.data == "set_qual")
async def toggle_quality(call: CallbackQuery, device_id: str, lang: str = "en"):
    rows = await db.select("settings", "screenshot_quality", {"device_id": device_id})
    if rows:
        current = rows[0].get("screenshot_quality", "high")
        new_qual = "low" if current == "high" else "high"
        await db.update("settings", {"screenshot_quality": new_qual}, {"device_id": device_id})

    settings_rows = await db.select("settings", "*", {"device_id": device_id})
    settings = settings_rows[0] if settings_rows else {}
    await call.message.edit_text(t("prefs_title", lang), reply_markup=settings_prefs_kb(settings, lang))
    await call.answer(t("quality_changed", lang, val=settings.get('screenshot_quality', 'high')))


@router.callback_query(F.data == "set_lang")
async def toggle_lang(call: CallbackQuery, device_id: str, lang: str = "en"):
    rows = await db.select("settings", "language", {"device_id": device_id})
    if rows:
        current = rows[0].get("language", "en")
        new_lang = "ua" if current == "en" else "en"
        await db.update("settings", {"language": new_lang}, {"device_id": device_id})
    else:
        new_lang = "ua"

    settings_rows = await db.select("settings", "*", {"device_id": device_id})
    settings = settings_rows[0] if settings_rows else {}
    await call.message.edit_text(t("prefs_title", new_lang), reply_markup=settings_prefs_kb(settings, new_lang))
    await call.answer(t("lang_changed", new_lang, val=new_lang.upper()))


# ── Disconnect ─────────────────────────────────────────────────

@router.callback_query(F.data == "disconnect_pc")
async def disconnect_pc(call: CallbackQuery, lang: str = "en"):
    await call.message.edit_text(t("ask_disconnect", lang), reply_markup=confirm_kb("disc", lang))
    await call.answer()


@router.callback_query(F.data == "disc_yes")
async def do_disconnect(call: CallbackQuery, device_id: str, lang: str = "en"):
    await db.update("connections", {"is_active": False}, {"device_id": device_id, "user_id": call.from_user.id})
    await log_action(device_id, call.from_user.id, call.from_user.username, "Disconnected PC")
    await call.message.edit_text(t("disconnected", lang))
    await call.answer()


# ── Device Info ────────────────────────────────────────────────

@router.callback_query(F.data == "sys_info")
async def sys_info(call: CallbackQuery, device_id: str, lang: str = "en"):
    rows = await db.select("connections", "connected_at", {"device_id": device_id, "user_id": call.from_user.id})
    conn_time = rows[0].get("connected_at") if rows else "Unknown"
    dev = await db.select_one("devices", "is_online, last_seen_at, name", {"id": device_id})

    online = await is_device_online(device_id)
    online_status = t("status_online", lang) if online else t("status_offline", lang)

    last_seen = dev.get("last_seen_at", "Unknown") if dev else "Unknown"
    dev_name = dev.get("name", "PC") if dev else "PC"

    text = (
        f"{t('info_title', lang)}\n\n"
        f"{t('info_name', lang, name=dev_name)}\n"
        f"{t('info_status', lang, status=online_status)}\n"
        f"{t('info_last_seen', lang, time=last_seen)}\n"
        f"{t('info_connected', lang, time=conn_time)}\n"
        f"{t('info_version', lang, ver='2026.5.19')}"
    )
    await call.message.edit_text(text, reply_markup=back_kb(lang), parse_mode="HTML")
    await call.answer()
