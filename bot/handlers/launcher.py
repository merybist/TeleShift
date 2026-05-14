import json
from aiogram import Router, F
from aiogram.types import CallbackQuery
from db import db
from keyboards.inline import apps_kb, back_kb
from utils.device import push_command, log_action, wait_for_result

router = Router()

@router.callback_query(F.data == "menu_launch")
async def menu_launch(call: CallbackQuery, device_id: str):
    rows = await db.select("apps", "*", {"device_id": device_id})
    if not rows:
        await call.message.edit_text("Немає програм. Додайте їх через додаток на ПК.", reply_markup=back_kb())
        return
    
    await call.message.edit_text("⏳ Перевіряю статус програм...")
    
    # Запитуємо статус у ПК
    payload = {"apps": [{"id": r["id"], "path": r["path"]} for r in rows]}
    cmd_id = await push_command(device_id, "check_apps", payload)
    result = await wait_for_result(cmd_id, timeout=10)
    
    status_map = {}
    if result and result != "timeout" and not result.startswith("Error"):
        try:
            status_map = json.loads(result)
        except:
            pass
            
    await call.message.edit_text("🚀 Запуск програм:", reply_markup=apps_kb(rows, status_map))

@router.callback_query(F.data.startswith("launch_"))
async def do_launch(call: CallbackQuery, device_id: str):
    app_id = call.data.split("_")[1]
    rows = await db.select("apps", "*", {"id": app_id})
    if rows:
        app_path = rows[0]["path"]
        app_name = rows[0]["name"]

        await call.message.edit_text(f"⏳ Запускаю {app_name}...")
        await log_action(device_id, call.from_user.id, call.from_user.username, f"Запустив {app_name}")

        cmd_id = await push_command(device_id, "launch_app", {"path": app_path})
        result = await wait_for_result(cmd_id)

        if result == "timeout":
             await call.message.edit_text("❌ Немає відповіді від ПК", reply_markup=back_kb())
        elif result == "success":
             await call.message.edit_text(f"✅ {app_name} запущена", reply_markup=back_kb())
        else:
             await call.message.edit_text(f"Помилка: {result}", reply_markup=back_kb())
