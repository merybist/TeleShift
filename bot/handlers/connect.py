from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from db import db
from keyboards.inline import connect_info_kb, main_menu_kb
from states.forms import ConnectForm
from utils.device import log_action

import re
import time

router = Router()

# Security: hash_token must be exactly 12 alphanumeric characters
HASH_TOKEN_REGEX = re.compile(r'^[a-zA-Z0-9_-]{12}$')

# Rate limit for connection attempts
CONNECT_RATE_LIMIT_MAX = 3
CONNECT_RATE_LIMIT_WINDOW = 60
_connect_attempts: dict[int, list[float]] = {}

@router.message(Command("start"))
async def cmd_start(message: Message, is_connected: bool, state: FSMContext):
    args = message.text.split()
    if len(args) > 1:
        hash_token = args[1]
        await process_hash(message, hash_token)
    elif is_connected:
        await message.answer("Main Menu", reply_markup=main_menu_kb())
    else:
        await message.answer("Your account is not connected to any PC.", reply_markup=connect_info_kb())

@router.callback_query(F.data == "connect_info")
async def connect_info(call: CallbackQuery):
    text = "To connect, scan the QR code in the app or enter the hash manually."
    await call.message.edit_text(text, reply_markup=connect_info_kb())

@router.callback_query(F.data == "enter_hash")
async def ask_hash(call: CallbackQuery, state: FSMContext):
    await call.message.edit_text("Enter the hash (12 characters):")
    await state.set_state(ConnectForm.hash)

@router.message(ConnectForm.hash)
async def receive_hash(message: Message, state: FSMContext):
    await process_hash(message, message.text)
    await state.clear()

async def process_hash(message: Message, hash_token: str):
    # Rate limit connection attempts
    user_id = message.from_user.id
    now = time.time()
    attempts = _connect_attempts.setdefault(user_id, [])
    attempts[:] = [t for t in attempts if now - t < CONNECT_RATE_LIMIT_WINDOW]
    if len(attempts) >= CONNECT_RATE_LIMIT_MAX:
        await message.answer("⏳ Too many attempts. Try again in 1 minute.")
        return
    attempts.append(now)

    # Validate hash_token format
    if not hash_token or not HASH_TOKEN_REGEX.match(hash_token):
        await message.answer("❌ Invalid token format. Must be exactly 12 characters.")
        return

    # Find connection by hash token
    rows = await db.select("connections", "*", {"hash_token": hash_token})

    if not rows:
        await message.answer("❌ Invalid token or token has expired.")
        return

    conn = rows[0]

    if conn["is_active"] and conn["user_id"] != message.from_user.id:
        await message.answer("❌ This token is already in use by another user. Generate a new one in the app.")
        return

    await db.update("connections", {
        "is_active": True,
        "user_id": message.from_user.id,
        "username": message.from_user.username,
        "first_name": message.from_user.first_name
    }, {"id": conn["id"]})

    await log_action(conn["device_id"], message.from_user.id, message.from_user.username, "Connected device")
    await message.answer("✅ PC successfully connected!\nMain Menu:", reply_markup=main_menu_kb())
