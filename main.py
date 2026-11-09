import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Подключаем роутеры из твоей папки bot
from bot.handlers import main_router

async def main():
    # Получаем токен прямо из переменных окружения Render
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token:
        logging.error("Ошибка: не найден BOT_TOKEN в переменных окружения Render!")
        sys.exit(1)

    # Инициализация бота для aiogram 3.x
    bot = Bot(
        token=bot_token, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Подключаем главный роутер с командами и сообщениями
    dp.include_router(main_router)

    # Удаляем вебхуки на случай зависших сессий и запускаем поллинг
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен и готов к работе!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Настройка логирования, чтобы видеть все ошибки в консоли Render
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен пользователем.")