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
            hostname = d.get('hostname', 'PC').replace('<', '&lt;').replace('>', '&gt;')
            os_info = d.get('os', 'N/A').replace('<', '&lt;').replace('>', '&gt;')
            
            # Розумний Аптайм
            uptime_s = d.get('uptime_seconds', d.get('uptime_hours', 0) * 3600)
            if uptime_s < 3600:
                uptime_str = f"{uptime_s // 60}хв"
            elif uptime_s < 86400:
                uptime_str = f"{uptime_s // 3600}г {(uptime_s % 3600) // 60}хв"
            else:
                days = uptime_s // 86400
                hours = (uptime_s % 86400) // 3600
                uptime_str = f"{days}д {hours}г"

            lines = [
                f"🖥 <b>{hostname}</b>",
                f"<code>{os_info}</code>",
                f"────────────────────",
                f"⚡ ЦП: <b>{d.get('cpu_load', 0)}%</b>",
                f"🧠 RAM: <b>{d.get('ram_used', 0)}</b> / {d.get('ram_total', 0)} GB (<b>{d.get('ram_percent', 0)}%</b>)",
                f"💾 Диск C: <b>{d.get('disk_free', 0)} GB</b> вільно",
            ]

            # GPU
            gpu_name = d.get('gpu_name', 'N/A')
            if gpu_name and gpu_name != 'N/A':
                gpu_name = gpu_name.replace('<', '&lt;').replace('>', '&gt;')
                gpu_line = f"🎮 GPU: <b>{gpu_name}</b>"
                if d.get('gpu_usage') is not None:
                    gpu_line += f" (<b>{d['gpu_usage']}%</b>)"
                if d.get('gpu_temp') is not None:
                    gpu_line += f" 🌡<b>{d['gpu_temp']}°C</b>"
                lines.append(gpu_line)

            # Battery
            battery = d.get('battery')
            if battery is not None and isinstance(battery, (int, float)):
                charge_icon = "🔌" if d.get('battery_charging') else "🔋"
                lines.append(f"{charge_icon} Батарея: <b>{battery}%</b>")

            lines.append(f"────────────────────")
            lines.append(f"⏱ Uptime: <b>{uptime_str}</b>")

            text = "\n".join(lines)
            await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
        except Exception as e:
            await call.message.edit_text(f"❌ Помилка обробки: {str(e)[:100]}", reply_markup=back_kb())

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
