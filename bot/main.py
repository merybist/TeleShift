import asyncio
import logging
from datetime import datetime, timezone, timedelta
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import db
from middleware.auth import AuthMiddleware
from handlers import connect, menu, power, status, screenshot, launcher, settings
from utils.i18n import t

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def online_watcher(bot: Bot):
    known_online: set[str] = set()
    while True:
        try:
            all_devices = await db.select("devices", "id, name, last_seen_at")
            now = datetime.now(timezone.utc)
            current_online = set()
            for d in all_devices:
                last_seen = d.get("last_seen_at")
                if last_seen:
                    if isinstance(last_seen, str):
                        try: last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                        except: continue
                    if (now - last_seen) < timedelta(seconds=60):
                        current_online.add(d["id"])

            newly_online = current_online - known_online
            for device_id in newly_online:
                set_row = await db.select_one("settings", "notify_online, language", {"device_id": device_id})
                if set_row and set_row.get("notify_online") is False: continue
                lang = set_row.get("language", "ua") if set_row else "ua"

                conns = await db.select("connections", "user_id", {"device_id": device_id, "is_active": True})
                device = await db.select_one("devices", "name", {"id": device_id})
                device_name = device.get("name", "PC") if device else "PC"

                for conn in conns:
                    try:
                        from keyboards.inline import main_menu_kb
                        await bot.send_message(
                            conn["user_id"],
                            f"🟢 *{device_name}* is now online!",
                            reply_markup=main_menu_kb(lang),
                            parse_mode="Markdown"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify user {conn['user_id']}: {e}")
            known_online = current_online
        except Exception as e:
            logger.error(f"Online watcher error: {e}")
        await asyncio.sleep(10)

async def scheduler_task(bot: Bot):
    while True:
        try:
            now = datetime.now()
            cur_time = now.strftime("%H:%M")
            rows = await db.select("scheduled_commands", "*", {"status": "pending"})
            for r in rows:
                sched_time = r['scheduled_at']
                if hasattr(sched_time, 'strftime'): sched_time = sched_time.strftime('%H:%M')
                else: sched_time = str(sched_time)[:5]
                
                if sched_time == cur_time:
                    last_run = r.get("last_run_at")
                    if last_run:
                        if isinstance(last_run, str): last_run = datetime.fromisoformat(last_run.replace("Z", "+00:00"))
                        if last_run.hour == now.hour and last_run.minute == now.minute: continue
                    
                    from utils.device import push_command
                    await push_command(r["device_id"], r["command"], user_id=r["user_id"])
                    
                    update_data = {"last_run_at": datetime.now(timezone.utc).isoformat()}
                    if not r["is_daily"]: update_data["status"] = "completed"
                    await db.update("scheduled_commands", update_data, {"id": r["id"]})
                    
                    set_row = await db.select_one("settings", "language", {"device_id": r["device_id"]})
                    lang = set_row.get("language", "ua") if set_row else "ua"
                    await bot.send_message(r["user_id"], f"⏰ {t('success', lang)}: {r['command']} executed.")
        except Exception as e:
            logger.error(f"Scheduler error: {e}")
        await asyncio.sleep(30)

async def main():
    await db.init()
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()
    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    dp.include_router(connect.router)
    dp.include_router(menu.router)
    dp.include_router(power.router)
    dp.include_router(status.router)
    dp.include_router(screenshot.router)
    dp.include_router(launcher.router)
    dp.include_router(settings.router)

    try:
        rows = await db.select("scheduled_commands", "*", {"status": "pending"})
        now_time = datetime.now().strftime("%H:%M")
        for r in rows:
            if not r["is_daily"] and r["scheduled_at"] < now_time:
                await db.update("scheduled_commands", {"status": "error"}, {"id": r["id"]})
                set_row = await db.select_one("settings", "language", {"device_id": r["device_id"]})
                lang = set_row.get("language", "ua") if set_row else "ua"
                await bot.send_message(r["user_id"], t('schedule_failed', lang, cmd=r['command'], time=r['scheduled_at']))
    except Exception as e: logger.error(f"Startup cleanup error: {e}")

    asyncio.create_task(online_watcher(bot))
    asyncio.create_task(scheduler_task(bot))

    print("TeleShift Bot is online")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
