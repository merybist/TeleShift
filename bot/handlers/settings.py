from aiogram import Router, F
from aiogram.types import CallbackQuery
from supabase_client import sb
from keyboards.inline import settings_kb, confirm_kb, back_kb
from utils.device import log_action

router = Router()

@router.callback_query(F.data == "menu_settings")
async def menu_settings(call: CallbackQuery, device_id: str):
    resp = sb.table("settings").select("*").eq("device_id", device_id).execute()
    settings = resp.data[0] if resp.data else {}
    await call.message.edit_text("⚙️ Налаштування", reply_markup=settings_kb(settings))

@router.callback_query(F.data == "disconnect_pc")
async def disconnect_pc(call: CallbackQuery):
    await call.message.edit_text("Відключити ПК від вашого акаунту?", reply_markup=confirm_kb("disc"))

@router.callback_query(F.data == "disc_yes")
async def do_disconnect(call: CallbackQuery, device_id: str):
    sb.table("connections").update({"is_active": False}).eq("device_id", device_id).eq("user_id", call.from_user.id).execute()
    log_action(device_id, call.from_user.id, call.from_user.username, "Відключив ПК")
    await call.message.edit_text("ПК успішно відключено від вашого акаунту.")

@router.callback_query(F.data == "sys_info")
async def sys_info(call: CallbackQuery, device_id: str):
    resp = sb.table("connections").select("connected_at").eq("device_id", device_id).eq("user_id", call.from_user.id).execute()
    conn_time = resp.data[0].get("connected_at") if resp.data else "Невідомо"
    text = f"ℹ️ Інфо\n\nDevice ID: {device_id}\nПідключено з: {conn_time}\nВерсія бота: 2.0.0 (Centralized)"
    await call.message.edit_text(text, reply_markup=back_kb())
