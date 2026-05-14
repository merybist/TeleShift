from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import confirm_kb
from utils.device import log_action, push_command

router = Router()

@router.callback_query(F.data == "power_off")
async def ask_power_off(call: CallbackQuery):
    await call.message.edit_text("Shut down PC now?", reply_markup=confirm_kb("off"))

@router.callback_query(F.data == "off_yes")
async def do_power_off(call: CallbackQuery, device_id: str):
    await log_action(device_id, call.from_user.id, call.from_user.username, "Shut down PC")
    await push_command(device_id, "shutdown")
    await call.message.edit_text("✅ Shutdown command sent to PC.")

@router.callback_query(F.data == "power_reboot")
async def ask_reboot(call: CallbackQuery):
    await call.message.edit_text("Restart PC now?", reply_markup=confirm_kb("reboot"))

@router.callback_query(F.data == "reboot_yes")
async def do_reboot(call: CallbackQuery, device_id: str):
    await log_action(device_id, call.from_user.id, call.from_user.username, "Restarted PC")
    await push_command(device_id, "reboot")
    await call.message.edit_text("✅ Restart command sent to PC.")

@router.callback_query(F.data == "sys_lock")
async def do_lock(call: CallbackQuery, device_id: str):
    await log_action(device_id, call.from_user.id, call.from_user.username, "Locked PC")
    await push_command(device_id, "lock")
    await call.answer("🔒 Lock command sent")
