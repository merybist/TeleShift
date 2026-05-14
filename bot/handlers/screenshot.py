import base64
import io
from aiogram import Router, F
from aiogram.types import CallbackQuery, URLInputFile, BufferedInputFile
from keyboards.inline import monitors_kb, back_kb
from utils.device import push_command, wait_for_result, log_action

router = Router()

@router.callback_query(F.data == "menu_screenshot")
async def menu_screen(call: CallbackQuery, device_id: str):
    await call.message.edit_text("📸 Taking screenshot...")
    await log_action(device_id, call.from_user.id, call.from_user.username, "Requested screenshot")

    cmd_id = await push_command(device_id, "take_screenshot")
    result = await wait_for_result(cmd_id, timeout=20)

    if result == "timeout":
        await call.message.edit_text("❌ PC is not responding.", reply_markup=back_kb())
    elif result.startswith("Error"):
        await call.message.edit_text(result, reply_markup=back_kb())
    else:
        try:
            if result.startswith("data:image") or result.startswith("iVBOR") or not result.startswith("http"):
                # Base64 encoded screenshot (raw PostgreSQL mode)
                raw = result.split(",", 1)[-1] if "," in result else result
                img_bytes = base64.b64decode(raw)
                photo = BufferedInputFile(img_bytes, filename="screenshot.png")
            else:
                # URL from Supabase Storage
                photo = URLInputFile(result)
            await call.message.answer_photo(photo, reply_markup=back_kb())
            await call.message.delete()
        except:
            await call.message.edit_text(f"Error loading photo.", reply_markup=back_kb())
