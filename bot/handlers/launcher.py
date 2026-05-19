import json
import logging
from aiogram import Router, F
from aiogram.types import CallbackQuery
from db import db
from locales import t
from keyboards.inline import apps_kb, launch_result_kb, back_kb
from utils.device import push_command, log_action, wait_for_result, RateLimitExceeded, DeviceOffline

logger = logging.getLogger(__name__)
router = Router()


@router.callback_query(F.data == "menu_launch")
async def menu_launch(call: CallbackQuery, device_id: str, lang: str = "en"):
    rows = await db.select("apps", "*", {"device_id": device_id})
    if not rows:
        await call.message.edit_text(t("launch_no_apps", lang), reply_markup=back_kb(lang))
        return

    await call.message.edit_text(t("launch_checking", lang))

    payload = {"apps": [{"id": r["id"], "path": r["path"]} for r in rows]}
    try:
        cmd_id = await push_command(device_id, "check_apps", payload, user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer(t("rate_limit", lang), show_alert=True)
        return
    except DeviceOffline:
        await call.answer(t("device_offline", lang), show_alert=True)
        return

    result = await wait_for_result(cmd_id, timeout=10)

    status_map = {}
    if result and result != "timeout" and not result.startswith("Error"):
        try:
            status_map = json.loads(result)
        except Exception as e:
            logger.error(f"Launcher status parse error: {e}")

    await call.message.edit_text(t("launch_title", lang), reply_markup=apps_kb(rows, status_map, lang))


@router.callback_query(F.data.startswith("launch_"))
async def do_launch(call: CallbackQuery, device_id: str, lang: str = "en"):
    app_id = call.data.split("_")[1]
    rows = await db.select("apps", "*", {"id": app_id})
    if rows:
        app_path = rows[0]["path"]
        app_name = rows[0]["name"]

        try:
            cmd_id = await push_command(device_id, "launch_app", {"path": app_path}, user_id=call.from_user.id)
        except RateLimitExceeded:
            await call.answer(t("rate_limit", lang), show_alert=True)
            return
        except DeviceOffline:
            await call.answer(t("device_offline", lang), show_alert=True)
            return

        await call.message.edit_text(t("launch_launching", lang, name=app_name))
        await log_action(device_id, call.from_user.id, call.from_user.username, f"Launched {app_name}")

        result = await wait_for_result(cmd_id)

        if result == "timeout":
            await call.message.edit_text(t("launch_no_response", lang), reply_markup=launch_result_kb(lang))
        elif result == "success":
            await call.message.edit_text(t("launch_success", lang, name=app_name), reply_markup=launch_result_kb(lang))
        else:
            await call.message.edit_text(t("launch_failed", lang), reply_markup=launch_result_kb(lang))
