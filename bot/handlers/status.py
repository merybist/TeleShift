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
            d = json.loads(result)
            lines = [
                "📊 *Статус ПК*\n",
                f"🖥 *{d.get('hostname', 'PC')}*",
                f"💻 {d.get('os', 'N/A')}\n",
                f"⚡ ЦП: *{d.get('cpu_load', 0)}%*",
                f"🧠 RAM: *{d.get('ram_used', 0)}* / {d.get('ram_total', 0)} GB ({d.get('ram_percent', 0)}%)",
                f"💾 Диск: *{d.get('disk_used', 0)}* / {d.get('disk_total', 0)} GB (вільно {d.get('disk_free', 0)} GB)",
            ]

            # GPU
            gpu_name = d.get('gpu_name', 'N/A')
            if gpu_name and gpu_name != 'N/A':
                gpu_line = f"🎮 GPU: *{gpu_name}*"
                if d.get('gpu_usage') is not None:
                    gpu_line += f" ({d['gpu_usage']}%)"
                if d.get('gpu_temp') is not None:
                    gpu_line += f" 🌡{d['gpu_temp']}°C"
                lines.append(gpu_line)

            # Battery (only if laptop and battery info is valid)
            battery = d.get('battery')
            if battery is not None and isinstance(battery, (int, float)):
                charge_icon = "⚡" if d.get('battery_charging') else ""
                lines.append(f"\n🔋 Батарея: *{battery}%* {charge_icon}")

            # Uptime
            uptime = d.get('uptime_hours', 0)
            if uptime >= 24:
                lines.append(f"\n⏱ Аптайм: {uptime // 24}д {uptime % 24}г")
            else:
                lines.append(f"\n⏱ Аптайм: {uptime}г")

            text = "\n".join(lines)
            await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="Markdown")
        except Exception as e:
            await call.message.edit_text(f"❌ Помилка обробки статусних даних: {e}", reply_markup=back_kb())

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
