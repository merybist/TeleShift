import json
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from locales import t
from keyboards.inline import status_menu_kb, back_kb
from utils.device import push_command, wait_for_result, RateLimitExceeded, DeviceOffline
from utils.telegram import handle_offline_device

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu_status")
async def menu_status(call: CallbackQuery, lang: str = "en"):
    await call.message.edit_text(t("btn_status", lang), reply_markup=status_menu_kb(lang))


@router.callback_query(F.data == "stat_all")
async def stat_all(call: CallbackQuery, device_id: str, lang: str = "en"):
    try:
        await call.message.edit_text(t("status_fetching", lang))
        cmd_id = await push_command(device_id, "get_status", user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer(t("rate_limit", lang), show_alert=True)
        return
    except DeviceOffline:
        await handle_offline_device(call, lang)
        return

    result = await wait_for_result(cmd_id)

    if result == "timeout":
        await call.message.edit_text(t("status_no_response", lang), reply_markup=back_kb(lang))
    else:
        try:
            d = json.loads(result)
            hostname = d.get('hostname', 'PC').replace('<', '&lt;').replace('>', '&gt;')
            os_info = d.get('os', 'N/A').replace('<', '&lt;').replace('>', '&gt;')
            uptime_val = d.get('uptime_seconds', 0)

            if isinstance(uptime_val, (int, float)) and uptime_val > 0:
                hours = int(uptime_val) // 3600
                minutes = (int(uptime_val) % 3600) // 60
                uptime_str = f"{hours}h {minutes}m"
            else:
                uptime_str = "N/A"

            lines = [
                f"📊 <b>{t('status_title', lang)}</b>\n",
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
                if d.get('gpu_usage') is not None:
                    gpu_line += f" (<b>{d['gpu_usage']}%</b>)"
                if d.get('gpu_temp') is not None:
                    gpu_line += f" 🌡<b>{d['gpu_temp']}°C</b>"
                lines.append(gpu_line)

            battery = d.get('battery')
            if battery is not None and isinstance(battery, (int, float)):
                charge_icon = "⚡" if d.get('battery_charging') else ""
                lines.append(f"\n🔋 Battery: <b>{battery}%</b> {charge_icon}")

            lines.append(f"────────────────────")
            lines.append(f"⏱ Uptime: <b>{uptime_str}</b>")

            text = "\n".join(lines)
            await call.message.edit_text(text, reply_markup=back_kb(lang), parse_mode="HTML")
        except Exception as e:
            logger.error(f"Status parse error: {e}")
            await call.message.edit_text(t("status_error", lang), reply_markup=back_kb(lang))
