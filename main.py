import asyncio
import logging
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message

# Мини-веб-сервер для Render, чтобы он видел открытый порт
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    
    # Отключаем лишние логи запросов в консоли
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logging.info(f"Веб-сервер запущен на порту {port}")
    server.serve_forever()

async def start_handler(message: Message):
    """Обработчик команды /start"""
    await message.answer(
        "Привет! Я твой Telegram-бот для работы с видео. "
        "Бот успешно запущен на Render и готов к работе! 🚀"
    )

async def main():
    # Запускаем веб-сервер в отдельном потоке, чтобы Render не ругался на порт
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

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

    # Регистрируем обработчик команды /start
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