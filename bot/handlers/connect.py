from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from supabase_client import sb
from keyboards.inline import connect_info_kb, main_menu_kb
from states.forms import ConnectForm
from utils.device import log_action

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, is_connected: bool, state: FSMContext):
    args = message.text.split()
    if len(args) > 1:
        hash_token = args[1]
        await process_hash(message, hash_token)
    elif is_connected:
        await message.answer("Головне меню", reply_markup=main_menu_kb())
    else:
        await message.answer("Ваш акаунт не підключено до жодного ПК.", reply_markup=connect_info_kb())

@router.callback_query(F.data == "connect_info")
async def connect_info(call: CallbackQuery):
    text = "Для підключення відскануйте QR-код в додатку або введіть хеш."
    await call.message.edit_text(text, reply_markup=connect_info_kb())

@router.callback_query(F.data == "enter_hash")
async def ask_hash(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Введіть хеш (12 символів):")
    await state.set_state(ConnectForm.hash)

@router.message(ConnectForm.hash)
async def receive_hash(message: Message, state: FSMContext):
    await process_hash(message, message.text)
    await state.clear()

async def process_hash(message: Message, hash_token: str):
    # Шукаємо підключення по хешу
    resp = sb.table("connections").select("*").eq("hash_token", hash_token).execute()
    
    if not resp.data:
        await message.answer("❌ Невірний токен або токен вже недійсний.")
        return
        
    conn = resp.data[0]
    
    if conn["is_active"] and conn["user_id"] != message.from_user.id:
        await message.answer("❌ Цей токен вже використовується іншим користувачем. Згенеруйте новий в додатку.")
        return

    sb.table("connections").update({
        "is_active": True,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name
    }).eq("id", conn["id"]).execute()
    
    log_action(conn["device_id"], message.from_user.id, message.from_user.username, "Підключив пристрій")
    await message.answer("✅ ПК успішно підключено!\nГоловне меню:", reply_markup=main_menu_kb())
