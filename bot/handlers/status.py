from aiogram import Router, F
from aiogram.types import CallbackQuery
from keyboards.inline import status_menu_kb, sound_menu_kb, back_kb
from utils.device import push_command, wait_for_result
from utils.i18n import t
import json

router = Router()

@router.callback_query(F.data == "menu_status")
async def menu_status(call: CallbackQuery, lang: str):
    await call.message.edit_text("📊 Select status:", reply_markup=status_menu_kb(lang))

@router.callback_query(F.data == "stat_all")
async def stat_all(call: CallbackQuery, device_id: str, lang: str):
    await call.message.edit_text(t('status_fetching', lang))
    cmd_id = await push_command(device_id, "get_status", user_id=call.from_user.id)
    result = await wait_for_result(cmd_id)
    if result == "timeout":
        await call.message.edit_text(t('error', lang, msg="PC Timeout"), reply_markup=back_kb(lang))
    else:
        try:
            d = json.loads(result)
            hostname = d.get('hostname', 'PC').replace('<', '&lt;').replace('>', '&gt;')
            os_info = d.get('os', 'N/A').replace('<', '&lt;').replace('>', '&gt;')
            lines = [
                f"📊 <b>PC Status</b>\n",
                f"🖥 <b>{hostname}</b>",
                f"💻 {os_info}\n",
                f"⚡ CPU: <b>{d.get('cpu_load', 0)}%</b>",
                f"🧠 RAM: <b>{d.get('ram_used', 0)}</b> / {d.get('ram_total', 0)} GB ({d.get('ram_percent', 0)}%)",
                f"💾 Disk: <b>{d.get('disk_used', 0)}</b> / {d.get('disk_total', 0)} GB (free {d.get('disk_free', 0)} GB)",
            ]
            gpu_name = d.get('gpu_name', 'N/A')
            if gpu_name and gpu_name != 'N/A':
                gpu_name = gpu_name.replace('<', '&lt;').replace('>', '&gt;')
                gpu_line = f"🎮 GPU: <b>{gpu_name}</b>"
                if d.get('gpu_usage') is not None: gpu_line += f" (<b>{d['gpu_usage']}%</b>)"
                if d.get('gpu_temp') is not None: gpu_line += f" 🌡<b>{d['gpu_temp']}°C</b>"
                lines.append(gpu_line)
            battery = d.get('battery')
            if battery is not None:
                charge_icon = "⚡" if d.get('battery_charging') else ""
                lines.append(f"\n🔋 Battery: <b>{battery}%</b> {charge_icon}")
            text = "\n".join(lines)
            await call.message.edit_text(text, reply_markup=back_kb(lang), parse_mode="HTML")
        except Exception as e:
            await call.message.edit_text(t('error', lang, msg=str(e)[:50]), reply_markup=back_kb(lang))

@router.callback_query(F.data == "stat_sound")
async def stat_sound(call: CallbackQuery, device_id: str, lang: str):
    await call.message.edit_text(t('status_fetching', lang))
    cmd_id = await push_command(device_id, "get_volume", user_id=call.from_user.id)
    result = await wait_for_result(cmd_id)
    if result == "timeout" or result.startswith("Error"):
        await call.message.edit_text(t('error', lang, msg="Sound fetch failed"), reply_markup=back_kb(lang))
    else:
        try:
            data = json.loads(result)
            vol = data.get("volume", 0)
            mute = data.get("muted", False)
            await call.message.edit_text(t('volume', lang, vol=vol), reply_markup=sound_menu_kb(vol, mute, lang))
        except:
            await call.message.edit_text(t('error', lang, msg="Data error"), reply_markup=back_kb(lang))

@router.callback_query(F.data.startswith("snd_"))
async def ctrl_sound(call: CallbackQuery, device_id: str, lang: str):
    action = call.data.split("_")[1]
    cmd_id = await push_command(device_id, "set_volume", {"action": action}, user_id=call.from_user.id)
    result = await wait_for_result(cmd_id)
    if result != "timeout" and not result.startswith("Error"):
        try:
            data = json.loads(result)
            vol = data.get("volume", 0)
            mute = data.get("muted", False)
            await call.message.edit_text(t('volume', lang, vol=vol), reply_markup=sound_menu_kb(vol, mute, lang))
            return
        except: pass
    await call.answer(t('error', lang, msg="Failed"))
