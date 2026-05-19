from aiogram import Router, F
from aiogram.types import CallbackQuery
from locales import t
from keyboards.inline import power_kb, confirm_kb, back_kb
from utils.device import log_action, push_command, RateLimitExceeded, DeviceOffline

router = Router()


@router.callback_query(F.data == "menu_power")
async def menu_power(call: CallbackQuery, lang: str = "en"):
    await call.message.edit_text(t("btn_power", lang), reply_markup=power_kb(lang))


@router.callback_query(F.data == "power_off")
async def ask_power_off(call: CallbackQuery, lang: str = "en"):
    await call.message.edit_text(t("ask_shutdown", lang), reply_markup=confirm_kb("off", lang))


@router.callback_query(F.data == "off_yes")
async def do_power_off(call: CallbackQuery, device_id: str, lang: str = "en"):
    try:
        await log_action(device_id, call.from_user.id, call.from_user.username, "Shut down PC")
        await push_command(device_id, "shutdown", user_id=call.from_user.id)
        await call.message.edit_text(t("shutdown_sent", lang), reply_markup=back_kb(lang))
    except RateLimitExceeded:
        await call.answer(t("rate_limit", lang), show_alert=True)
    except DeviceOffline:
        await call.answer(t("device_offline", lang), show_alert=True)


@router.callback_query(F.data == "power_reboot")
async def ask_reboot(call: CallbackQuery, lang: str = "en"):
    await call.message.edit_text(t("ask_restart", lang), reply_markup=confirm_kb("reboot", lang))


@router.callback_query(F.data == "reboot_yes")
async def do_reboot(call: CallbackQuery, device_id: str, lang: str = "en"):
    try:
        await log_action(device_id, call.from_user.id, call.from_user.username, "Restarted PC")
        await push_command(device_id, "reboot", user_id=call.from_user.id)
        await call.message.edit_text(t("restart_sent", lang), reply_markup=back_kb(lang))
    except RateLimitExceeded:
        await call.answer(t("rate_limit", lang), show_alert=True)
    except DeviceOffline:
        await call.answer(t("device_offline", lang), show_alert=True)
