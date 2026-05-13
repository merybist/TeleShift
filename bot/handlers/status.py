from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import status_menu_kb, sound_menu_kb, back_kb
from utils.device import push_command, wait_for_result, log_action
import json

router = Router()

@router.callback_query(F.data == "menu_status")
async def menu_status(call: CallbackQuery):
    await call.message.edit_text("📊 Оберіть статус:", reply_markup=status_menu_kb())

@router.callback_query(F.data == "stat_all")
async def stat_all(call: CallbackQuery, device_id: str):
    await call.message.edit_text("⏳ Отримую статус з ПК...")
    cmd_id = await push_command(device_id, "get_status")
    result = await wait_for_result(cmd_id)

    if result == "timeout":
        await call.message.edit_text("❌ ПК не відповідає. Перевірте підключення додатка.", reply_markup=back_kb())
    else:
        try:
            data = json.loads(result)
            text = f"🔋 Батарея: {data.get('battery', 'Немає')}%\n💾 Диск C: {data.get('disk_free', 0)}GB вільно"
            await call.message.edit_text(text, reply_markup=back_kb())
        except:
            await call.message.edit_text(result, reply_markup=back_kb())

@router.callback_query(F.data == "stat_sound")
async def stat_sound(call: CallbackQuery, device_id: str):
    await call.message.edit_text("⏳ Отримую статус звуку...")
    cmd_id = await push_command(device_id, "get_volume")
    result = await wait_for_result(cmd_id)

    if result == "timeout" or result.startswith("Помилка"):
        await call.message.edit_text("❌ Помилка отримання звуку", reply_markup=back_kb())
    else:
        try:
            data = json.loads(result)
            vol = data.get("volume", 0)
            mute = data.get("muted", False)
            await call.message.edit_text(f"🔊 Гучність: {vol}%", reply_markup=sound_menu_kb(vol, mute))
        except:
            await call.message.edit_text("Помилка формату даних", reply_markup=back_kb())

@router.callback_query(F.data.startswith("snd_"))
async def ctrl_sound(call: CallbackQuery, device_id: str):
    action = call.data.split("_")[1]

    cmd_id = await push_command(device_id, "set_volume", {"action": action})
    await call.message.edit_text("⏳ Змінюю...")
    result = await wait_for_result(cmd_id)

    if result == "timeout" or result.startswith("Помилка"):
        await call.message.edit_text("❌ Помилка", reply_markup=back_kb())
    else:
        try:
            data = json.loads(result)
            vol = data.get("volume", 0)
            mute = data.get("muted", False)
            await call.message.edit_text(f"🔊 Гучність: {vol}%", reply_markup=sound_menu_kb(vol, mute))
        except:
            await call.message.edit_text("Помилка формату даних", reply_markup=back_kb())
