import asyncio
import logging
import os
import sys
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)

# Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
REQUIRED_CHANNEL = "@hf_motion"  # Канал для проверки подписки
DOWNLOAD_DIR = Path("/tmp/tg_video_bot")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Мини-веб-сервер для Render (чтобы держать порт открытым)
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive!")
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# Проверка подписки пользователя на канал
async def check_subscription(bot: Bot, user_id: int) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        # Статусы, при которых считается, что пользователь подписан
        if member.status in ["creator", "administrator", "member"]:
            return True
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
    return False

# Клавиатура для непрописанных пользователей
def get_subscribe_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📢 Подписаться на канал", url="https://t.me/hf_motion")],
        [InlineKeyboardButton(text="✅ Я подписался", callback_data="check_sub")]
    ])

# Клавиатура выбора для YouTube (Видео или Музыка)
def get_youtube_keyboard(url: str):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🎥 Видео", callback_data=f"dl_vid:{url}"),
            InlineKeyboardButton(text="🎵 Музыка (MP3)", callback_data=f"dl_aud:{url}")
        ]
    ])

# Обработчик /start
async def start_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    if not await check_subscription(bot, user_id):
        await message.answer(
            f"👋 Привет! Чтобы пользоваться ботом, подпишись на наш официальный канал {REQUIRED_CHANNEL}!",
            reply_markup=get_subscribe_keyboard()
        )
        return

    await message.answer(
        "👋 Привет! Я твой бот-скачивальщик.\n\n"
        "🔗 Отправь мне ссылку из:\n"
        "• **YouTube** (предложу видео или музыку)\n"
        "• **Instagram** (посты, Reels и истории)\n"
        "• **TikTok** (без водяных знаков)\n"
        "• **Pinterest**"
    )

# Обработка нажатия кнопки "Я подписался"
async def verify_subscription(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    if await check_subscription(bot, user_id):
        await callback.message.edit_text("✅ Спасибо за подписку! Теперь отправь мне ссылку на видео.")
    else:
        await callback.answer("❌ Вы еще не подписались на канал!", show_alert=True)

# Обработка входящих ссылок
async def url_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    if not await check_subscription(bot, user_id):
        await message.answer(
            f"❌ Для использования бота необходимо подписаться на канал {REQUIRED_CHANNEL}!",
            reply_markup=get_subscribe_keyboard()
        )
        return

    url = message.text.strip()
    
    # Определяем платформу по ссылке
    if "youtube.com" in url or "youtu.be" in url:
        await message.answer("⏳ Ссылка на YouTube обнаружена. Что вы хотите скачать?", reply_markup=get_youtube_keyboard(url))
    elif any(domain in url for domain in ["instagram.com", "tiktok.com", "pin.it", "pinterest.com"]):
        await message.answer("⏳ Скачиваю медиафайл, подождите пару секунд...")
        await download_and_send_media(message, url, mode="video")
    else:
        await message.answer("⚠️ Пожалуйста, отправьте корректную ссылку на YouTube, Instagram, TikTok или Pinterest.")

# Функция скачивания и отправки через yt-dlp
async def download_and_send_media(message: Message, url: str, mode: str = "video"):
    loop = asyncio.get_running_loop()
    
    ydl_opts = {
        'outtmpl': str(DOWNLOAD_DIR / '%(id)s.%(ext)s'),
        'noplaylist': True,
    }

    if mode == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    else:
        ydl_opts.update({
            'format': 'bestvideo+bestaudio/best',
        })

    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if mode == "audio":
                filename = str(Path(filename).with_suffix('.mp3'))
            return filename, info.get('title', 'media')

    try:
        file_path, title = await loop.run_in_executor(None, download)
        
        if mode == "audio":
            await message.answer_audio(audio=FSInputFile(file_path), caption=title)
        else:
            await message.answer_video(video=FSInputFile(file_path), caption=title)
            
        # Удаляем файл после отправки
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Ошибка скачивания: {e}")
        await message.answer("❌ Не удалось скачать файл. Проверьте правильность ссылки или попробуйте другую.")

# Обработка кнопок выбора YouTube (Видео / Аудио)
async def youtube_callback_handler(callback: CallbackQuery):
    data = callback.data
    action, url = data.split(":", 1)
    
    await callback.message.edit_text("⏳ Загружаю файл, подождите...")
    
    if action == "dl_vid":
        await download_and_send_media(callback.message, url, mode="video")
    elif action == "dl_aud":
        await download_and_send_media(callback.message, url, mode="audio")

async def main():
    # Запуск веб-сервер в фоне
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    if not BOT_TOKEN:
        logging.error("Не найден BOT_TOKEN!")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Регистрация хендлеров
    dp.message.register(start_handler, CommandStart())
    dp.callback_query.register(verify_subscription, F.data == "check_sub")
    dp.callback_query.register(youtube_callback_handler, F.data.startswith("dl_"))
    dp.message.register(url_handler, F.text.startswith("http"))

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот-скачивальщик запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")