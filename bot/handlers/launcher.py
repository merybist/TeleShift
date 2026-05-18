import json
from aiogram import Router, F
from aiogram.types import CallbackQuery
from db import db
from keyboards.inline import apps_kb, back_kb
from utils.device import push_command, log_action, wait_for_result, RateLimitExceeded

router = Router()

@router.callback_query(F.data == "menu_launch")
async def menu_launch(call: CallbackQuery, device_id: str):
    rows = await db.select("apps", "*", {"device_id": device_id})
    if not rows:
        await call.message.edit_text("No apps found. Add them via the PC agent.", reply_markup=back_kb())
        return

    await call.message.edit_text("⏳ Checking app statuses...")

    # Request app status from PC
    payload = {"apps": [{"id": r["id"], "path": r["path"]} for r in rows]}
    try:
        cmd_id = await push_command(device_id, "check_apps", payload, user_id=call.from_user.id)
    except RateLimitExceeded:
        await call.answer("⚠️ Too many commands. Please wait a moment.", show_alert=True)
        return
    result = await wait_for_result(cmd_id, timeout=10)

    status_map = {}
    if result and result != "timeout" and not result.startswith("Error"):
        try:
            status_map = json.loads(result)
        except:
            pass

    await call.message.edit_text("🚀 App Launcher:", reply_markup=apps_kb(rows, status_map))

@router.callback_query(F.data.startswith("launch_"))
async def do_launch(call: CallbackQuery, device_id: str):
    app_id = call.data.split("_")[1]
    rows = await db.select("apps", "*", {"id": app_id})
    if rows:
        app_path = rows[0]["path"]
        app_name = rows[0]["name"]

        try:
            cmd_id = await push_command(device_id, "launch_app", {"path": app_path}, user_id=call.from_user.id)
        except RateLimitExceeded:
            await call.answer("⚠️ Too many commands. Please wait a moment.", show_alert=True)
            return

        await call.message.edit_text(f"⏳ Launching {app_name}...")
        await log_action(device_id, call.from_user.id, call.from_user.username, f"Launched {app_name}")

        result = await wait_for_result(cmd_id)

        if result == "timeout":
             await call.message.edit_text("❌ No response from PC", reply_markup=back_kb())
        elif result == "success":
             await call.message.edit_text(f"✅ {app_name} launched", reply_markup=back_kb())
        else:
             await call.message.edit_text("❌ Failed to launch application.", reply_markup=back_kb())
