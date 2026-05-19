from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from db import db
from locales import t
from keyboards.inline import connect_info_kb, main_menu_kb
from states.forms import ConnectForm
from utils.device import log_action

import re
import time

router = Router()

HASH_TOKEN_REGEX = re.compile(r'^[a-zA-Z0-9_-]{12}$')


@router.message(Command("start"))
async def cmd_start(message: Message, is_connected: bool, lang: str = "en", state: FSMContext = None):
    args = message.text.split()
    if len(args) > 1:
        hash_token = args[1]
        await process_hash(message, hash_token, lang)
    elif is_connected:
        await message.answer(t("main_menu", lang), reply_markup=main_menu_kb(lang))
    else:
        await message.answer(t("not_connected", lang), reply_markup=connect_info_kb(lang))


@router.callback_query(F.data == "connect_info")
async def connect_info(call: CallbackQuery, lang: str = "en"):
    await call.message.edit_text(t("connect_info", lang), reply_markup=connect_info_kb(lang))


@router.callback_query(F.data == "enter_hash")
async def ask_hash(call: CallbackQuery, lang: str = "en", state: FSMContext = None):
    await call.message.edit_text(t("enter_hash_prompt", lang))
    await state.set_state(ConnectForm.hash)


@router.message(ConnectForm.hash)
async def receive_hash(message: Message, lang: str = "en", state: FSMContext = None):
    await process_hash(message, message.text, lang)
    await state.clear()


async def process_hash(message: Message, hash_token: str, lang: str = "en"):
    if not hash_token or not HASH_TOKEN_REGEX.match(hash_token):
        await message.answer(t("invalid_token", lang))
        return

    rows = await db.select("connections", "*", {"hash_token": hash_token})

    if not rows:
        await message.answer(t("token_expired", lang))
        return

    conn = rows[0]

    if conn["is_active"] and conn["user_id"] != message.from_user.id:
        await message.answer(t("token_in_use", lang))
        return

    await db.update("connections", {
        "is_active": True,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name
    }, {"id": conn["id"]})

    # Create default settings row if not exists
    existing_settings = await db.select_one("settings", "device_id", {"device_id": conn["device_id"]})
    if not existing_settings:
        await db.insert("settings", {
            "device_id": conn["device_id"],
            "notify_on_command": True,
            "notify_online": True,
            "screenshot_quality": "high",
            "language": "en"
        })

    await log_action(conn["device_id"], message.from_user.id, message.from_user.username, "Connected device")
    await message.answer(t("connected_success", lang), reply_markup=main_menu_kb(lang))
