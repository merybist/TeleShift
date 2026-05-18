import base64
import json
import io
from aiogram import Router, F
from aiogram.types import CallbackQuery, URLInputFile, BufferedInputFile
from keyboards.inline import monitors_kb, back_kb
from utils.device import push_command, wait_for_result, log_action, RateLimitExceeded
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

router = Router()

@router.callback_query(F.data == "menu_screenshot")
async def menu_screen(call: CallbackQuery, device_id: str):
    try:
        cmd_id = await push_command(device_id, "take_screenshot", user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer("⚠️ Too many commands. Please wait a moment.", show_alert=True)
        return

    await call.message.edit_text("📸 Taking screenshot...")
    await log_action(device_id, call.from_user.id, call.from_user.username, "Requested screenshot")

    result = await wait_for_result(cmd_id, timeout=20)

    if result == "timeout":
        await call.message.edit_text("❌ PC is not responding.", reply_markup=back_kb())
    elif result.startswith("Error"):
        await call.message.edit_text("❌ Failed to capture screenshot.", reply_markup=back_kb())
    else:
        try:
            # Try to parse as encrypted payload (new format)
            payload = json.loads(result)
            if "encrypted" in payload and "key" in payload and "iv" in payload and "authTag" in payload:
                # Decrypt AES-256-GCM encrypted screenshot
                key = base64.b64decode(payload["key"])
                iv = base64.b64decode(payload["iv"])
                auth_tag = base64.b64decode(payload["authTag"])
                encrypted_data = base64.b64decode(payload["encrypted"])
                # GCM ciphertext + tag concatenated for decryption
                aesgcm = AESGCM(key)
                img_bytes = aesgcm.decrypt(iv, encrypted_data + auth_tag, None)
                photo = BufferedInputFile(img_bytes, filename="screenshot.png")
            else:
                raise ValueError("Unknown payload format")
        except (json.JSONDecodeError, ValueError, KeyError):
            # Legacy format: base64 or URL
            if result.startswith("data:image") or result.startswith("iVBOR") or not result.startswith("http"):
                raw = result.split(",", 1)[-1] if "," in result else result
                img_bytes = base64.b64decode(raw)
                photo = BufferedInputFile(img_bytes, filename="screenshot.png")
            else:
                photo = URLInputFile(result)
        except Exception:
            await call.message.edit_text("❌ Error decrypting screenshot.", reply_markup=back_kb())
            return

        try:
            await call.message.answer_photo(photo, reply_markup=back_kb())
            await call.message.delete()
        except:
            await call.message.edit_text("❌ Error loading photo.", reply_markup=back_kb())
