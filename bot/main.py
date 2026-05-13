import asyncio
import logging
from aiogram import Bot, Dispatcher
from config import BOT_TOKEN
from middleware.auth import AuthMiddleware
from handlers import connect, menu, power, status, screenshot, launcher, settings

logging.basicConfig(level=logging.INFO)

async def main():
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

    print("Bot is starting polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
