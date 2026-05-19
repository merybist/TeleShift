import asyncio
import logging
from datetime import datetime, timezone, timedelta

from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import db
from middleware.auth import AuthMiddleware
from keyboards.inline import main_menu_kb
from utils.device import is_device_online
from handlers import connect, menu, power, status, screenshot, launcher, settings, controls

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def online_watcher(bot: Bot):
    """Background task: watches for devices going online and notifies users."""
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
                        try:
                            last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                        except Exception:
                            continue
                    if last_seen.tzinfo is None:
                        last_seen = last_seen.replace(tzinfo=timezone.utc)
                    if (now - last_seen) < timedelta(seconds=60):
                        current_online.add(d["id"])

            newly_online = current_online - known_online

            for device_id in newly_online:
                settings_rows = await db.select("settings", "notify_online, language", {"device_id": device_id})
                if settings_rows and settings_rows[0].get("notify_online") is False:
                    continue

                lang = settings_rows[0].get("language", "en") if settings_rows else "en"

                conns = await db.select("connections", "user_id", {"device_id": device_id, "is_active": True})
                device = await db.select_one("devices", "name", {"id": device_id})
                device_name = device.get("name", "PC") if device else "PC"

                from locales import t
                for conn in conns:
                    try:
                        await bot.send_message(
                            conn["user_id"],
                            t("online_notification", lang, name=device_name),
                            reply_markup=main_menu_kb(lang),
                            parse_mode="Markdown"
                        )
                        logger.info(f"Notified user {conn['user_id']} about device {device_id} online")
                    except Exception as e:
                        logger.error(f"Failed to notify user {conn['user_id']}: {e}")

            known_online = current_online

        except Exception as e:
            logger.error(f"Online watcher error: {e}")

        await asyncio.sleep(10)


async def cleanup_old_commands():
    """Background task: deletes completed/error commands older than 2 days."""
    while True:
        try:
            await db.delete_old_commands(days=2)
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
        await asyncio.sleep(3600)


async def main():
    await db.init()

    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher()

    dp.message.middleware(AuthMiddleware())
    dp.callback_query.middleware(AuthMiddleware())

    dp.include_router(connect.router)
    dp.include_router(menu.router)
    dp.include_router(power.router)
    dp.include_router(controls.router)
    dp.include_router(status.router)
    dp.include_router(screenshot.router)
    dp.include_router(launcher.router)
    dp.include_router(settings.router)

    asyncio.create_task(online_watcher(bot))
    asyncio.create_task(cleanup_old_commands())

    print("Bot is starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
