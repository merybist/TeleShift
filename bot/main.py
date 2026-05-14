import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from db import db
from middleware.auth import AuthMiddleware
from handlers import connect, menu, power, status, screenshot, launcher, settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def online_watcher(bot: Bot):
    """Background task: watches for devices going online and notifies users."""
    known_online: set[str] = set()  # device IDs we already notified about

    while True:
        try:
            # Get all devices and check last_seen_at within 60 seconds
            all_devices = await db.select("devices", "id, name, last_seen_at")
            from datetime import datetime, timezone, timedelta
            now = datetime.now(timezone.utc)
            current_online = set()
            for d in all_devices:
                last_seen = d.get("last_seen_at")
                if last_seen:
                    if isinstance(last_seen, str):
                        try:
                            last_seen = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                        except:
                            continue
                    if (now - last_seen) < timedelta(seconds=60):
                        current_online.add(d["id"])

            # Find newly online devices (not in our known set)
            newly_online = current_online - known_online

            for device_id in newly_online:
                # Check if notifications are enabled for this device
                settings_rows = await db.select("settings", "notify_online", {"device_id": device_id})
                if settings_rows and settings_rows[0].get("notify_online") is False:
                    continue

                # Find connected users for this device
                conns = await db.select("connections", "user_id", {"device_id": device_id, "is_active": True})
                device = await db.select_one("devices", "name", {"id": device_id})
                device_name = device.get("name", "PC") if device else "PC"

                for conn in conns:
                    try:
                        from keyboards.inline import main_menu_kb
                        await bot.send_message(
                            conn["user_id"],
                            f"🟢 *{device_name}* is now online!",
                            reply_markup=main_menu_kb(),
                            parse_mode="Markdown"
                        )
                        logger.info(f"Notified user {conn['user_id']} about device {device_id} online")
                    except Exception as e:
                        logger.error(f"Failed to notify user {conn['user_id']}: {e}")

            # Remove devices that went offline from known set
            known_online = current_online

        except Exception as e:
            logger.error(f"Online watcher error: {e}")

        await asyncio.sleep(10)


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

    # Start background online watcher
    asyncio.create_task(online_watcher(bot))

    print("Bot is starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
