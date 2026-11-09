import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

# Подключаем роутер из файла handlers.py, который лежит в корне проекта
from handlers import router

async def main():
    # Получаем токен из переменных окружения Render
    bot_token = os.getenv("BOT_TOKEN")
    
    if not bot_token:
        logging.error("Ошибка: не найден BOT_TOKEN в переменных окружения Render!")
        sys.exit(1)

    # Инициализация бота
    bot = Bot(
        token=bot_token, 
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()

    # Подключаем роутер
    dp.include_router(router)

    # Запуск поллинга
    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот успешно запущен и готов к работе!")
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        stream=sys.stdout
    )
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен пользователем.")