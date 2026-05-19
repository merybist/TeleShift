from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import status_menu_kb, sound_menu_kb, back_kb
from utils.device import push_command, wait_for_result, log_action, RateLimitExceeded
import json

router = Router()

@router.callback_query(F.data == "menu_status")
async def menu_status(call: CallbackQuery):
    await call.message.edit_text("📊 Select status:", reply_markup=status_menu_kb())

@router.callback_query(F.data == "stat_all")
async def stat_all(call: CallbackQuery, device_id: str):
    try:
        await call.message.edit_text("⏳ Fetching PC status...")
        cmd_id = await push_command(device_id, "get_status", user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer("⚠️ Too many commands. Please wait a moment.", show_alert=True)
        return
    result = await wait_for_result(cmd_id)

    if result == "timeout":
        await call.message.edit_text("❌ PC is not responding. Check the agent connection.", reply_markup=back_kb())
    else:
        try:
            d = json.loads(result)
            hostname = d.get('hostname', 'PC').replace('<', '&lt;').replace('>', '&gt;')
            os_info = d.get('os', 'N/A').replace('<', '&lt;').replace('>', '&gt;')
            uptime_val = d.get('uptime', 'N/A')
            
            lines = [
                f"📊 <b>PC Status</b>\n",
                f"🖥 <b>{hostname}</b>",
                f"💻 {os_info}\n",
                f"⚡ CPU: <b>{d.get('cpu_load', 0)}%</b>",
                f"🧠 RAM: <b>{d.get('ram_used', 0)}</b> / {d.get('ram_total', 0)} GB ({d.get('ram_percent', 0)}%)",
                f"💾 Disk: <b>{d.get('disk_used', 0)}</b> / {d.get('disk_total', 0)} GB (free {d.get('disk_free', 0)} GB)",
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
                charge_icon = "⚡" if d.get('battery_charging') else ""
                lines.append(f"\n🔋 Battery: <b>{battery}%</b> {charge_icon}")

            lines.append(f"────────────────────")
            lines.append(f"⏱ Uptime: <b>{uptime_val}</b>")

            text = "\n".join(lines)
            await call.message.edit_text(text, reply_markup=back_kb(), parse_mode="HTML")
        except Exception:
            await call.message.edit_text("❌ An error occurred while processing status data. Please try again.", reply_markup=back_kb())

@router.callback_query(F.data == "stat_sound")
async def stat_sound(call: CallbackQuery, device_id: str):
    try:
        await call.message.edit_text("⏳ Fetching sound status...")
        cmd_id = await push_command(device_id, "get_volume", user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer("⚠️ Too many commands. Please wait a moment.", show_alert=True)
        return
    result = await wait_for_result(cmd_id)

    if result == "timeout" or result.startswith("Error"):
        await call.message.edit_text("❌ Error fetching sound", reply_markup=back_kb())
    else:
        try:
            data = json.loads(result)
            vol = data.get("volume", 0)
            mute = data.get("muted", False)
            await call.message.edit_text(f"🔊 Volume: {vol}%", reply_markup=sound_menu_kb(vol, mute))
        except (json.JSONDecodeError, KeyError, TypeError):
            await call.message.edit_text("Data format error", reply_markup=back_kb())

@router.callback_query(F.data.startswith("snd_"))
async def ctrl_sound(call: CallbackQuery, device_id: str):
    action = call.data.split("_")[1]

    try:
        cmd_id = await push_command(device_id, "set_volume", {"action": action}, user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer("⚠️ Too many commands. Please wait a moment.", show_alert=True)
        return
    await call.message.edit_text("⏳ Changing...")
    result = await wait_for_result(cmd_id)

    if result == "timeout" or result.startswith("Error"):
        await call.message.edit_text("❌ Error", reply_markup=back_kb())
    else:
        try:
            data = json.loads(result)
            vol = data.get("volume", 0)
            mute = data.get("muted", False)
            await call.message.edit_text(f"🔊 Volume: {vol}%", reply_markup=sound_menu_kb(vol, mute))
        except (json.JSONDecodeError, KeyError, TypeError):
            await call.message.edit_text("Data format error", reply_markup=back_kb())
