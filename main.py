import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from config import settings
from bot.middlewares import I18nMiddleware, RateLimitMiddleware
from bot.handlers import main_router
from bot.services import queue_manager, file_cleaner

logging.basicConfig(level=logging.DEBUG if settings.DEBUG else logging.INFO, stream=sys.stdout)
logger = logging.getLogger("tg_video_bot")

async def main():
    settings.validate()
    bot = Bot(token=settings.BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.update.outer_middleware(I18nMiddleware())
    dp.message.middleware(RateLimitMiddleware())
    dp.callback_query.middleware(RateLimitMiddleware())
    dp.include_router(main_router)

    file_cleaner.cleanup_stale_files()
    await queue_manager.start()
    
    logger.info("Bot started successfully.")
    try:
        await dp.start_polling(bót if 'bót' in globals() else bot, skip_updates=True)
    finally:
        await queue_manager.stop()
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(main())
