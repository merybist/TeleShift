import re
from aiogram import Router, F
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext
from db import db
from keyboards.inline import confirm_kb, power_control_kb, schedule_type_kb, schedules_list_kb, back_kb
from utils.device import log_action, push_command
from utils.i18n import t
from states.forms import ScheduleForm

router = Router()

@router.callback_query(F.data == "menu_power")
async def menu_power(call: CallbackQuery, lang: str):
    await call.message.edit_text(t('power_title', lang), reply_markup=power_control_kb(lang))

@router.callback_query(F.data == "power_off")
async def ask_power_off(call: CallbackQuery, lang: str):
    await call.message.edit_text(t('shutdown_confirm', lang), reply_markup=confirm_kb("off", lang))

@router.callback_query(F.data == "off_yes")
async def do_power_off(call: CallbackQuery, device_id: str, lang: str):
    await log_action(device_id, call.from_user.id, call.from_user.username, "Shut down PC")
    await push_command(device_id, "shutdown", user_id=call.from_user.id)
    await call.message.edit_text(t('success', lang), reply_markup=back_kb(lang))

@router.callback_query(F.data == "power_reboot")
async def ask_reboot(call: CallbackQuery, lang: str):
    await call.message.edit_text(t('reboot_confirm', lang), reply_markup=confirm_kb("reboot", lang))

@router.callback_query(F.data == "reboot_yes")
async def do_reboot(call: CallbackQuery, device_id: str, lang: str):
    await log_action(device_id, call.from_user.id, call.from_user.username, "Restarted PC")
    await push_command(device_id, "reboot", user_id=call.from_user.id)
    await call.message.edit_text(t('success', lang), reply_markup=back_kb(lang))

@router.callback_query(F.data == "sys_lock")
async def do_lock(call: CallbackQuery, device_id: str, lang: str):
    await log_action(device_id, call.from_user.id, call.from_user.username, "Locked PC")
    await push_command(device_id, "lock", user_id=call.from_user.id)
    await call.answer(t('lock_confirm', lang))

@router.callback_query(F.data.startswith("sched_"))
async def sched_router(call: CallbackQuery, state: FSMContext, lang: str, device_id: str):
    action = call.data.split("_")[1]
    if action in ["shutdown", "reboot"]:
        await state.update_data(command=action)
        await state.set_state(ScheduleForm.time)
        await call.message.edit_text(t('enter_time', lang), reply_markup=back_kb(lang))
    elif action == "list":
        rows = await db.select("scheduled_commands", "*", {"device_id": device_id, "status": "pending"})
        await call.message.edit_text(t('my_schedules', lang), reply_markup=schedules_list_kb(rows, lang))
    elif action == "del":
        sched_id = call.data.split("_")[2]
        await db.update("scheduled_commands", {"status": "cancelled"}, {"id": sched_id})
        rows = await db.select("scheduled_commands", "*", {"device_id": device_id, "status": "pending"})
        await call.answer(t('schedule_cancelled', lang))
        await call.message.edit_text(t('my_schedules', lang), reply_markup=schedules_list_kb(rows, lang))

@router.message(ScheduleForm.time)
async def sched_time(message: Message, state: FSMContext, lang: str):
    time_str = message.text.strip()
    if not re.match(r'^([01]?[0-9]|2[0-3]):[0-5][0-9]$', time_str):
        await message.answer(t('invalid_time', lang))
        return
    await state.update_data(time=time_str)
    await state.set_state(ScheduleForm.type)
    await message.answer(t('select_type', lang), reply_markup=schedule_type_kb(lang))

@router.callback_query(F.data.startswith("stype_"), ScheduleForm.type)
async def sched_finish(call: CallbackQuery, state: FSMContext, lang: str, device_id: str):
    stype = call.data.split("_")[1]
    data = await state.get_data()
    await state.clear()
    await db.insert("scheduled_commands", {
        "device_id": device_id,
        "user_id": call.from_user.id,
        "command": data['command'],
        "scheduled_at": data['time'],
        "is_daily": (stype == "daily"),
        "status": "pending"
    })
    msg = t('schedule_set', lang, cmd=data['command'], time=data['time'], type=t('daily' if stype == "daily" else 'one_time', lang))
    await call.message.edit_text(msg, reply_markup=back_kb(lang))
