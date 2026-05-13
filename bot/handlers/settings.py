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
    await call.message.edit_text("⚙️ Налаштування", reply_markup=settings_kb(settings))

@router.callback_query(F.data == "disconnect_pc")
async def disconnect_pc(call: CallbackQuery):
    await call.message.edit_text("Відключити ПК від вашого акаунту?", reply_markup=confirm_kb("disc"))

@router.callback_query(F.data == "disc_yes")
async def do_disconnect(call: CallbackQuery, device_id: str):
    await db.update("connections", {"is_active": False}, {"device_id": device_id, "user_id": call.from_user.id})
    await log_action(device_id, call.from_user.id, call.from_user.username, "Відключив ПК")
    await call.message.edit_text("ПК успішно відключено від вашого акаунту.")

@router.callback_query(F.data == "sys_info")
async def sys_info(call: CallbackQuery, device_id: str):
    rows = await db.select("connections", "connected_at", {"device_id": device_id, "user_id": call.from_user.id})
    conn_time = rows[0].get("connected_at") if rows else "Невідомо"

    # Check online status
    dev = await db.select_one("devices", "is_online, last_seen_at, name", {"id": device_id})
    online_status = "🟢 Онлайн" if dev and dev.get("is_online") else "🔴 Офлайн"
    last_seen = dev.get("last_seen_at", "Невідомо") if dev else "Невідомо"
    dev_name = dev.get("name", "ПК") if dev else "ПК"

    text = (
        f"ℹ️ *Інфо*\n\n"
        f"🖥 Назва: *{dev_name}*\n"
        f"📡 Статус: {online_status}\n"
        f"🕐 Останній раз: {last_seen}\n"
        f"🔗 Підключено з: {conn_time}\n"
        f"📦 Версія бота: 2.1.0"
    )
    await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")

@router.callback_query(F.data == "set_online_notif")
async def toggle_online_notif(call: CallbackQuery, device_id: str):
    rows = await db.select("settings", "*", {"device_id": device_id})
    if rows:
        current = rows[0].get("notify_online", True)
        await db.update("settings", {"notify_online": not current}, {"device_id": device_id})
    settings = (await db.select("settings", "*", {"device_id": device_id}))[0] if rows else {}
    await call.message.edit_text("⚙️ Налаштування", reply_markup=settings_kb(settings))
