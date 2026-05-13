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
            # Get all online devices
            rows = await db.select("devices", "id, name, is_online", {"is_online": True})
            current_online = {r["id"] for r in rows}

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
                device_name = device.get("name", "ПК") if device else "ПК"

                for conn in conns:
                    try:
                        from keyboards.inline import main_menu_kb
                        await bot.send_message(
                            conn["user_id"],
                            f"🟢 *{device_name}* з'явився в мережі!",
                            reply_markup=main_menu_kb(),
                            parse_mode="Markdown"
                        )
                        logger.info(f"Notified user {conn['user_id']} about device {device_id} online")
                    except Exception as e:
                        logger.error(f"Failed to notify user {conn['user_id']}: {e}")

            # Update known set
            known_online = current_online

        except Exception as e:
            logger.error(f"Online watcher error: {e}")

        await asyncio.sleep(5)


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
