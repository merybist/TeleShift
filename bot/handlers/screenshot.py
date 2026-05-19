import base64
import json
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery, URLInputFile, BufferedInputFile
from locales import t
from keyboards.inline import back_kb
from utils.device import push_command, wait_for_result, log_action, RateLimitExceeded, DeviceOffline
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from db import db

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu_screenshot")
async def menu_screen(call: CallbackQuery, device_id: str, lang: str = "en"):
    try:
        cmd_id = await push_command(device_id, "take_screenshot", payload={"quality": quality}, user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer(t("rate_limit", lang), show_alert=True)
        return
    except DeviceOffline:
        await call.answer(t("device_offline", lang), show_alert=True)
        return

    await call.message.edit_text(t("screenshot_taking", lang))
    await log_action(device_id, call.from_user.id, call.from_user.username, "Requested screenshot")

    result = await wait_for_result(cmd_id, timeout=20)

    if result == "timeout":
        await call.message.edit_text(t("screenshot_no_response", lang), reply_markup=back_kb(lang))
    elif result.startswith("Error"):
        await call.message.edit_text(t("screenshot_failed", lang), reply_markup=back_kb(lang))
    else:
        try:
            payload = json.loads(result)
            if "encrypted" in payload and "key" in payload and "iv" in payload and "authTag" in payload:
                key = base64.b64decode(payload["key"])
                iv = base64.b64decode(payload["iv"])
                auth_tag = base64.b64decode(payload["authTag"])
                encrypted_data = base64.b64decode(payload["encrypted"])
                aesgcm = AESGCM(key)
                img_bytes = aesgcm.decrypt(iv, encrypted_data + auth_tag, None)
                photo = BufferedInputFile(img_bytes, filename="screenshot.png")
            else:
                raise ValueError("Unknown payload format")
        except (json.JSONDecodeError, ValueError, KeyError):
            if result.startswith("data:image") or result.startswith("iVBOR") or not result.startswith("http"):
                raw = result.split(",", 1)[-1] if "," in result else result
                img_bytes = base64.b64decode(raw)
                photo = BufferedInputFile(img_bytes, filename="screenshot.png")
            else:
                photo = URLInputFile(result)
        except Exception as e:
            logger.error(f"Screenshot decrypt error: {e}")
            await call.message.edit_text(t("screenshot_decrypt_error", lang), reply_markup=back_kb(lang))
            return

        try:
            await call.message.answer_photo(photo, reply_markup=back_kb(lang))
            await call.message.delete()
        except Exception as e:
            logger.error(f"Screenshot send error: {e}")
            await call.message.edit_text(t("screenshot_load_error", lang), reply_markup=back_kb(lang))
