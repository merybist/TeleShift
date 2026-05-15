import base64
from aiogram import Router, F
from aiogram.types import CallbackQuery, URLInputFile, BufferedInputFile
from keyboards.inline import monitors_kb, back_kb
from utils.device import push_command, wait_for_result, log_action
from utils.i18n import t
from db import db

router = Router()

@router.callback_query(F.data == "menu_screenshot")
async def menu_screen(call: CallbackQuery, device_id: str, lang: str):
    dev = await db.select_one("devices", "monitor_count", {"id": device_id})
    count = dev.get("monitor_count", 1) if dev else 1
    if count > 1:
        await call.message.edit_text("📺 Select monitor:", reply_markup=monitors_kb(count, lang))
    else:
        await take_screen(call, device_id, lang, "all")

@router.callback_query(F.data.startswith("screen_"))
async def take_screen(call: CallbackQuery, device_id: str, lang: str, monitor: str = None):
    if not monitor:
        monitor = call.data.split("_")[1]
    await call.message.edit_text(t('screenshot_taking', lang))
    await log_action(device_id, call.from_user.id, call.from_user.username, f"Screenshot (Monitor {monitor})")

    cmd_id = await push_command(device_id, "take_screenshot", {"monitor": monitor}, user_id=call.from_user.id)
    result = await wait_for_result(cmd_id, timeout=20)

    if result == "timeout":
        await call.message.edit_text(t('error', lang, msg="Timeout"), reply_markup=back_kb(lang))
    elif result.startswith("Error"):
        await call.message.edit_text(result, reply_markup=back_kb(lang))
    else:
        try:
            if result.startswith("data:image") or result.startswith("iVBOR") or not result.startswith("http"):
                raw = result.split(",", 1)[-1] if "," in result else result
                img_bytes = base64.b64decode(raw)
                photo = BufferedInputFile(img_bytes, filename="screenshot.png")
            else:
                photo = URLInputFile(result)
            await call.message.answer_photo(photo, reply_markup=back_kb(lang))
            await call.message.delete()
        except:
            await call.message.edit_text(t('error', lang, msg="Load failed"), reply_markup=back_kb(lang))
