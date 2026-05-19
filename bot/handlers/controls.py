import json
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from locales import t
from keyboards.inline import controls_kb, sound_menu_kb, confirm_kb, back_kb
from utils.device import push_command, wait_for_result, log_action, RateLimitExceeded, DeviceOffline

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu_controls")
async def menu_controls(call: CallbackQuery, lang: str = "en"):
    await call.message.edit_text(t("controls_title", lang), reply_markup=controls_kb(lang))


# ── Lock ───────────────────────────────────────────────────────

@router.callback_query(F.data == "ctrl_lock")
async def ask_lock(call: CallbackQuery, lang: str = "en"):
    await call.message.edit_text(t("ask_lock", lang), reply_markup=confirm_kb("lock", lang))


@router.callback_query(F.data == "lock_yes")
async def do_lock(call: CallbackQuery, device_id: str, lang: str = "en"):
    try:
        await log_action(device_id, call.from_user.id, call.from_user.username, "Locked PC")
        await push_command(device_id, "lock", user_id=call.from_user.id)
        await call.message.edit_text(t("lock_sent", lang), reply_markup=back_kb(lang))
    except RateLimitExceeded:
        await call.answer(t("rate_limit", lang), show_alert=True)
    except DeviceOffline:
        await call.answer(t("device_offline", lang), show_alert=True)


# ── Sound ──────────────────────────────────────────────────────

@router.callback_query(F.data == "ctrl_sound")
async def ctrl_sound(call: CallbackQuery, device_id: str, lang: str = "en"):
    try:
        await call.message.edit_text(t("sound_fetching", lang))
        cmd_id = await push_command(device_id, "get_volume", user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer(t("rate_limit", lang), show_alert=True)
        return
    except DeviceOffline:
        await call.answer(t("device_offline", lang), show_alert=True)
        return

    result = await wait_for_result(cmd_id)

    if result == "timeout" or result.startswith("Error"):
        await call.message.edit_text(t("sound_error", lang), reply_markup=back_kb(lang))
    else:
        try:
            data = json.loads(result)
            vol = data.get("volume", 0)
            mute = data.get("muted", False)
            await call.message.edit_text(t("sound_volume", lang, vol=vol), reply_markup=sound_menu_kb(vol, mute, lang))
        except Exception as e:
            logger.error(f"Sound parse error: {e}")
            await call.message.edit_text(t("data_format_error", lang), reply_markup=back_kb(lang))


@router.callback_query(F.data.startswith("snd_"))
async def handle_sound(call: CallbackQuery, device_id: str, lang: str = "en"):
    action = call.data.split("_")[1]

    try:
        cmd_id = await push_command(device_id, "set_volume", {"action": action}, user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer(t("rate_limit", lang), show_alert=True)
        return
    except DeviceOffline:
        await call.answer(t("device_offline", lang), show_alert=True)
        return

    await call.message.edit_text(t("sound_changing", lang))
    result = await wait_for_result(cmd_id)

    if result == "timeout" or result.startswith("Error"):
        await call.message.edit_text(t("sound_error", lang), reply_markup=back_kb(lang))
    else:
        try:
            data = json.loads(result)
            vol = data.get("volume", 0)
            mute = data.get("muted", False)
            await call.message.edit_text(t("sound_volume", lang, vol=vol), reply_markup=sound_menu_kb(vol, mute, lang))
        except Exception as e:
            logger.error(f"Sound parse error: {e}")
            await call.message.edit_text(t("data_format_error", lang), reply_markup=back_kb(lang))
