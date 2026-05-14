from aiogram import Router, F
from aiogram.types import CallbackQuery
from db import db
from keyboards.inline import settings_kb, confirm_kb, back_kb
from utils.device import log_action

router = Router()

@router.callback_query(F.data == "menu_settings")
async def menu_settings(call: CallbackQuery, device_id: str):
    rows = await db.select("settings", "*", {"device_id": device_id})
    settings = rows[0] if rows else {}
    await call.message.edit_text("⚙️ Settings", reply_markup=settings_kb(settings))

@router.callback_query(F.data == "set_notif")
async def toggle_notif(call: CallbackQuery, device_id: str):
    rows = await db.select("settings", "notify_on_command", {"device_id": device_id})
    if rows:
        current = rows[0].get("notify_on_command", False)
        await db.update("settings", {"notify_on_command": not current}, {"device_id": device_id})
    
    settings_rows = await db.select("settings", "*", {"device_id": device_id})
    settings = settings_rows[0] if settings_rows else {}
    await call.message.edit_text("⚙️ Settings", reply_markup=settings_kb(settings))
    await call.answer("Notifications updated")

@router.callback_query(F.data == "set_qual")
async def toggle_quality(call: CallbackQuery, device_id: str):
    rows = await db.select("settings", "screenshot_quality", {"device_id": device_id})
    if rows:
        current = rows[0].get("screenshot_quality", "high")
        new_qual = "low" if current == "high" else "high"
        await db.update("settings", {"screenshot_quality": new_qual}, {"device_id": device_id})
    
    settings_rows = await db.select("settings", "*", {"device_id": device_id})
    settings = settings_rows[0] if settings_rows else {}
    await call.message.edit_text("⚙️ Settings", reply_markup=settings_kb(settings))
    await call.answer(f"Quality changed to {settings.get('screenshot_quality')}")

@router.callback_query(F.data == "set_lang")
async def toggle_lang(call: CallbackQuery, device_id: str):
    rows = await db.select("settings", "language", {"device_id": device_id})
    if rows:
        current = rows[0].get("language", "ua")
        new_lang = "en" if current == "ua" else "ua"
        await db.update("settings", {"language": new_lang}, {"device_id": device_id})
    
    settings_rows = await db.select("settings", "*", {"device_id": device_id})
    settings = settings_rows[0] if settings_rows else {}
    await call.message.edit_text("⚙️ Settings", reply_markup=settings_kb(settings))
    await call.answer(f"Language changed to {settings.get('language').upper()}")

@router.callback_query(F.data == "set_online_notif")
async def toggle_online_notif(call: CallbackQuery, device_id: str):
    rows = await db.select("settings", "notify_online", {"device_id": device_id})
    if rows:
        current = rows[0].get("notify_online", True)
        await db.update("settings", {"notify_online": not current}, {"device_id": device_id})
    
    settings_rows = await db.select("settings", "*", {"device_id": device_id})
    settings = settings_rows[0] if settings_rows else {}
    await call.message.edit_text("⚙️ Settings", reply_markup=settings_kb(settings))
    await call.answer("Online notification changed")

@router.callback_query(F.data == "disconnect_pc")
async def disconnect_pc(call: CallbackQuery):
    await call.message.edit_text("Disconnect PC from your account?", reply_markup=confirm_kb("disc"))
    await call.answer()

@router.callback_query(F.data == "disc_yes")
async def do_disconnect(call: CallbackQuery, device_id: str):
    await db.update("connections", {"is_active": False}, {"device_id": device_id, "user_id": call.from_user.id})
    await log_action(device_id, call.from_user.id, call.from_user.username, "Disconnected PC")
    await call.message.edit_text("PC successfully disconnected from your account.")
    await call.answer("PC disconnected")

@router.callback_query(F.data == "sys_info")
async def sys_info(call: CallbackQuery, device_id: str):
    rows = await db.select("connections", "connected_at", {"device_id": device_id, "user_id": call.from_user.id})
    conn_time = rows[0].get("connected_at") if rows else "Unknown"
    dev = await db.select_one("devices", "is_online, last_seen_at, name", {"id": device_id})
    online_status = "🟢 Online" if dev and dev.get("is_online") else "🔴 Offline"
    last_seen = dev.get("last_seen_at", "Unknown") if dev else "Unknown"
    dev_name = dev.get("name", "PC") if dev else "PC"

    text = (
        f"ℹ️ <b>Info</b>\n\n"
        f"🖥 Name: <b>{dev_name}</b>\n"
        f"📡 Status: {online_status}\n"
        f"🕐 Last seen: {last_seen}\n"
        f"🔗 Connected since: {conn_time}\n"
        f"📦 Version: 1.0.5"
    )
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
    await call.answer()
