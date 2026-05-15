import json
from aiogram import Router, F
from aiogram.types import CallbackQuery
from db import db
from keyboards.inline import apps_kb, back_kb
from utils.device import push_command, log_action, wait_for_result
from utils.i18n import t

router = Router()

@router.callback_query(F.data == "menu_launch")
async def menu_launch(call: CallbackQuery, device_id: str, lang: str):
    rows = await db.select("apps", "*", {"device_id": device_id})
    if not rows:
        await call.message.edit_text(t('no_apps', lang), reply_markup=back_kb(lang))
        return
    await call.message.edit_text(t('status_fetching', lang))
    payload = {"apps": [{"id": r["id"], "path": r["path"]} for r in rows]}
    cmd_id = await push_command(device_id, "check_apps", payload, user_id=call.from_user.id)
    result = await wait_for_result(cmd_id, timeout=10)
    status_map = {}
    if result and result != "timeout" and not result.startswith("Error"):
        try: status_map = json.loads(result)
        except: pass
    await call.message.edit_text(t('launcher_title', lang), reply_markup=apps_kb(rows, status_map, lang))

@router.callback_query(F.data.startswith("launch_"))
async def do_launch(call: CallbackQuery, device_id: str, lang: str):
    app_id = call.data.split("_")[1]
    rows = await db.select("apps", "*", {"id": app_id})
    if rows:
        app_path = rows[0]["path"]
        app_name = rows[0]["name"]
        await call.message.edit_text(t('launching', lang, name=app_name))
        await log_action(device_id, call.from_user.id, call.from_user.username, f"Launched {app_name}")
        cmd_id = await push_command(device_id, "launch_app", {"path": app_path}, user_id=call.from_user.id)
        result = await wait_for_result(cmd_id)
        if result == "success":
             await call.message.edit_text(t('launched', lang, name=app_name), reply_markup=back_kb(lang))
        else:
             await call.message.edit_text(t('error', lang, msg=result), reply_markup=back_kb(lang))
