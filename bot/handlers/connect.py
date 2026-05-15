from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from db import db
from keyboards.inline import connect_info_kb, main_menu_kb
from states.forms import ConnectForm
from utils.device import log_action
from utils.i18n import t

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message, is_connected: bool, state: FSMContext, lang: str):
    args = message.text.split()
    if len(args) > 1:
        hash_token = args[1]
        await process_hash(message, hash_token, lang)
    elif is_connected:
        await message.answer(f"🏠 {t('welcome', lang)}", reply_markup=main_menu_kb(lang), parse_mode="HTML")
    else:
        await message.answer(t('not_connected', lang), reply_markup=connect_info_kb(lang))

@router.callback_query(F.data == "connect_info")
async def connect_info(call: CallbackQuery, lang: str):
    text = "To connect, scan the QR code in the app or enter the hash manually."
    await call.message.edit_text(text, reply_markup=connect_info_kb(lang))

@router.callback_query(F.data == "enter_hash")
async def ask_hash(call: CallbackQuery, state: FSMContext, lang: str):
    await call.message.edit_text(t('enter_hash', lang))
    await state.set_state(ConnectForm.hash)

@router.message(ConnectForm.hash)
async def receive_hash(message: Message, state: FSMContext, lang: str):
    await process_hash(message, message.text, lang)
    await state.clear()

async def process_hash(message: Message, hash_token: str, lang: str):
    rows = await db.select("connections", "*", {"hash_token": hash_token})
    if not rows:
        await message.answer(t('invalid_token', lang))
        return

    conn = rows[0]
    if conn["is_active"] and conn["user_id"] != message.from_user.id:
        await message.answer(t('token_in_use', lang))
        return

    await db.update("connections", {
        "is_active": True,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name
    }, {"id": conn["id"]})

    await log_action(conn["device_id"], message.from_user.id, message.from_user.username, "Connected device")
    await message.answer(t('success', lang), reply_markup=main_menu_kb(lang))
