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
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)

# Настройки
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6051384649# <--- Укажи сюда свой Telegram ID (цифрами), чтобы управлять ботом
DOWNLOAD_DIR = Path("/tmp/tg_video_bot")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

# База данных в памяти (можно настроить каналы и языки прямо из бота)
bot_settings = {
    "channels": ["@raqami77"],  # Каналы для проверки подписки
    "languages": {
        "tg": {
            "name": "🇹🇯 Тоҷикӣ",
            "start": "Салом! Лутфан ба канали мо обуна шавед:",
            "sub_btn": "📢 Обуна шудан",
            "check_btn": "✅ Ман обуна шудам",
            "not_sub": "❌ Шумо ҳанӯз обуна нашудаед!",
            "send_link": "🔗 Истинодро фиристед (YouTube, Instagram, TikTok, Pinterest):",
            "yt_choice": "🎥 Видепоро интихоб кунед ё мусиқӣ:",
            "vid_btn": "🎥 Видео",
            "aud_btn": "🎵 Мусиқӣ (MP3)",
            "downloading": "⏳ Боргирӣ истодааст, лутфан интизор шавед...",
            "error": "❌ Боргирӣ муваффақ نشд. Истинодро санҷед."
        },
        "uz": {
            "name": "🇺🇿 O'zbekcha",
            "start": "Salom! Botdan foydalanish uchun kanalimizga obuna bo'ling:",
            "sub_btn": "📢 Obuna bo'lish",
            "check_btn": "✅ Obuna bo'ldim",
            "not_sub": "❌ Siz hali kanalga obuna bo'lmadingiz!",
            "send_link": "🔗 Havolani yuboring (YouTube, Instagram, TikTok, Pinterest):",
            "yt_choice": "🎥 Videoni yoki musiqani tanlang:",
            "vid_btn": "🎥 Video",
            "aud_btn": "🎵 Musiqa (MP3)",
            "downloading": "⏳ Yuklab olinmoqda, iltimos kuting...",
            "error": "❌ Yuklab bo'lmadi. Havolani tekshiring."
        },
        "kk": {
            "name": "🇰🇿 Қазақша",
            "start": "Сәлем! Ботты қолдану үшін арнамызға жазылыңыз:",
            "sub_btn": "📢 Жазылу",
            "check_btn": "✅ Мен жазылдым",
            "not_sub": "❌ Сіз әлі арнаға жазылған жоқсыз!",
            "send_link": "🔗 Сілтемені жіберіңіз (YouTube, Instagram, TikTok, Pinterest):",
            "yt_choice": "🎥 Бейнені немесе музыканы таңдаңыз:",
            "vid_btn": "🎥 Бейне",
            "aud_btn": "🎵 Музыка (MP3)",
            "downloading": "⏳ Жүктелуде, күте тұрыңыз...",
            "error": "❌ Жүктелмеді. Сілтемені тексеріңіз."
        },
        "ru": {
            "name": "🇷🇺 Русский",
            "start": "Привет! Для использования бота подпишись на наш канал:",
            "sub_btn": "📢 Подписаться",
            "check_btn": "✅ Я подписался",
            "not_sub": "❌ Вы еще не подписались на канал!",
            "send_link": "🔗 Отправь мне ссылку (YouTube, Instagram, TikTok, Pinterest):",
            "yt_choice": "🎥 Что вы хотите скачать?",
            "vid_btn": "🎥 Видео",
            "aud_btn": "🎵 Музыка (MP3)",
            "downloading": "⏳ Скачиваю файл, подождите...",
            "error": "❌ Не удалось скачать файл. Проверьте ссылку."
        }
    }
}

user_lang = {}  # Хранит выбранный язык пользователей

# Веб-сервер для Render
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

# Проверка подписки на все активные каналы
async def check_all_subscriptions(bot: Bot, user_id: int) -> bool:
    for channel in bot_settings["channels"]:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["creator", "administrator", "member"]:
                return False
        except Exception as e:
            logging.error(f"Ошибка проверки канала {channel}: {e}")
            return False
    return True

# Выбор языка (клавиатура)
def get_language_keyboard():
    keyboard = []
    for code, data in bot_settings["languages"].items():
        keyboard.append([InlineKeyboardButton(text=data["name"], callback_data=f"lang_{code}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Команда /start
async def start_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, "ru")  # По умолчанию русский
    texts = bot_settings["languages"][lang]

    # Проверка подписки
    if not await check_all_subscriptions(bot, user_id):
        channels_text = "\n".join([f"• {ch}" for ch in bot_settings["channels"]])
        keyboard = [
            [InlineKeyboardButton(text=texts["sub_btn"], url=f"https://t.me/{bot_settings['channels'][0].replace('@', '')}")],
            [InlineKeyboardButton(text=texts["check_btn"], callback_data="check_sub")],
            [InlineKeyboardButton(text="🌐 Изменить язык / Язык", callback_data="change_lang")]
        ]
        await message.answer(f"{texts['start']}\n{channels_text}", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
        return

    keyboard = [
        [InlineKeyboardButton(text="🌐 Язык / Language", callback_data="change_lang")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])

    await message.answer(texts["send_link"], reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# Смена языка
async def change_lang_callback(callback: CallbackQuery):
    await callback.message.edit_text("Выберите язык / Лутфан забонро интихоб кунед:", reply_markup=get_language_keyboard())

async def set_language_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang_code = callback.data.split("_")[1]
    user_lang[user_id] = lang_code
    await callback.message.edit_text("✅ Язык изменен! Отправьте команду /start")

# Админ-панель
async def admin_panel_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔️ Доступ запрещен", show_alert=True)
    
    channels_str = ", ".join(bot_settings["channels"])
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="admin_add_channel")],
        [InlineKeyboardButton(text="➖ Удалить канал", callback_data="admin_del_channel")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    await callback.message.edit_text(f"⚙️ **Админ-панель**\n\nТекущие каналы: {channels_str}", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

async def admin_actions(callback: CallbackQuery, message: Message = None):
    # Управление каналами через чат
    data = callback.data
    if data == "admin_add_channel":
        await callback.message.answer("Отправьте @username канала, который нужно добавить (например, @newchannel):")
    elif data == "admin_del_channel":
        await callback.message.answer(f"Текущие каналы: {', '.join(bot_settings['channels'])}. Напишите канал для удаления:")

# Обработка входящих ссылок
async def url_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, "ru")
    texts = bot_settings["languages"][lang]

    if not await check_all_subscriptions(bot, user_id):
        await message.answer(texts["not_sub"])
        return

    url = message.text.strip()
    if "youtube.com" in url or "youtu.be" in url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=texts["vid_btn"], callback_data=f"dl_vid:{url}"),
                InlineKeyboardButton(text=texts["aud_btn"], callback_data=f"dl_aud:{url}")
            ]
        ])
        await message.answer(texts["yt_choice"], reply_markup=keyboard)
    elif any(domain in url for domain in ["instagram.com", "tiktok.com", "pin.it", "pinterest.com"]):
        await message.answer(texts["downloading"])
        await download_and_send_media(message, url, mode="video", lang=lang)
    else:
        await message.answer("⚠️ Неверная ссылка.")

# Скачивание медиа
async def download_and_send_media(message: Message, url: str, mode: str = "video", lang: str = "ru"):
    texts = bot_settings["languages"][lang]
    loop = asyncio.get_running_loop()
    ydl_opts = {
        'outtmpl': str(DOWNLOAD_DIR / '%(id)s.%(ext)s'),
        'noplaylist': True,
    }
    if mode == "audio":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}],
        })
    else:
        ydl_opts.update({'format': 'bestvideo+bestaudio/best'})

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
        os.remove(file_path)
    except Exception as e:
        logging.error(f"Ошибка: {e}")
        await message.answer(texts["error"])

async def youtube_callback_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = user_lang.get(user_id, "ru")
    texts = bot_settings["languages"][lang]
    
    data = callback.data
    action, url = data.split(":", 1)
    await callback.message.edit_text(texts["downloading"])
    
    if action == "dl_vid":
        await download_and_send_media(callback.message, url, mode="video", lang=lang)
    elif action == "dl_aud":
        await download_and_send_media(callback.message, url, mode="audio", lang=lang)

async def main():
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    if not BOT_TOKEN:
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # Регистрация
    dp.message.register(start_handler, CommandStart())
    dp.callback_query.register(change_lang_callback, F.data == "change_lang")
    dp.callback_query.register(set_language_callback, F.data.startswith("lang_"))
    dp.callback_query.register(admin_panel_callback, F.data == "admin_panel")
    dp.callback_query.register(youtube_callback_handler, F.data.startswith("dl_"))
    dp.message.register(url_handler, F.text.startswith("http"))

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Многоязычный бот запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")