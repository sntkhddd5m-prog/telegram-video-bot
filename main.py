import asyncio
import logging
import os
import sys

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

async def start_handler(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "Привет! Я твой Telegram-бот для работы с видео. "
        "Бот успешно запущен на Render и готов к работе! 🚀"
    )

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

    # Регистрируем обработчик команды /start прямо здесь
    dp.message.register(start_handler, CommandStart())

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