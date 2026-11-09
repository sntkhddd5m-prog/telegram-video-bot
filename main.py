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

# ==================== НАСТРОЙКИ БОТА ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 6051384649  # Твой ID администратора

# Текст приветствия (можешь менять его здесь!)
WELCOME_TEXT_CUSTOM = (
    "👋 Привет! Я твой бот-скачивальщик.\n\n"
    "🔗 Отправь мне ссылку из:\n"
    "• YouTube (видео или музыка)\n"
    "• Instagram (посты, Reels, истории)\n"
    "• TikTok (без водяных знаков)\n"
    "• Pinterest"
)

REQUIRED_CHANNEL = "@raqami_77"  # Исправленный канал с подчеркиванием
DOWNLOAD_DIR = Path("/tmp/tg_video_bot")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
# ========================================================

translations = {
    "tg": {
        "name": "🇹🇯 Тоҷикӣ",
        "sub_text": "Салом! Барои истифодаи бот лутфан ба канали мо обуна шавед:",
        "sub_btn": "📢 Обуна шудан",
        "check_btn": "✅ Ман обуна шудам",
        "not_sub": "❌ Шумо ҳанӯз обуна нашудаед!",
        "send_link": "🔗 Истинодро фиристед:",
        "yt_choice": "🎥 Видепоро интихоб кунед ё мусиқӣ:",
        "vid_btn": "🎥 Видео",
        "aud_btn": "🎵 Мусиқӣ (MP3)",
        "downloading": "⏳ Боргирӣ истодааст...",
        "error": "❌ Хатогӣ рух дод. Истинодро санҷед."
    },
    "uz": {
        "name": "🇺🇿 O'zbekcha",
        "sub_text": "Salom! Botdan foydalanish uchun kanalimizga obuna bo'ling:",
        "sub_btn": "📢 Obuna bo'lish",
        "check_btn": "✅ Obuna bo'ldim",
        "not_sub": "❌ Siz hali kanalga obuna bo'lmadingiz!",
        "send_link": "🔗 Havolani yuboring:",
        "yt_choice": "🎥 Videoni yoki musiqani tanlang:",
        "vid_btn": "🎥 Video",
        "aud_btn": "🎵 Musiqa (MP3)",
        "downloading": "⏳ Yuklab olinmoqda...",
        "error": "❌ Xatolik yuz berdi. Havolani tekshiring."
    },
    "kk": {
        "name": "🇰🇿 Қазақша",
        "sub_text": "Сәлем! Ботты қолдану үшін арнамызға жазылыңыз:",
        "sub_btn": "📢 Жазылу",
        "check_btn": "✅ Мен жазылдым",
        "not_sub": "❌ Сіз әлі арнаға жазылған жоқсыз!",
        "send_link": "🔗 Сілтемені жіберіңіз:",
        "yt_choice": "🎥 Бейнені немесе музыканы таңдаңыз:",
        "vid_btn": "🎥 Бейне",
        "aud_btn": "🎵 Музыка (MP3)",
        "downloading": "⏳ Жүктелуде...",
        "error": "❌ Қате орын алды. Сілтемені тексеріңіз."
    },
    "ru": {
        "name": "🇷🇺 Русский",
        "sub_text": "Привет! Для использования бота подпишись на наш канал:",
        "sub_btn": "📢 Подписаться",
        "check_btn": "✅ Я подписался",
        "not_sub": "❌ Вы еще не подписались на канал!",
        "send_link": "🔗 Отправь мне ссылку:",
        "yt_choice": "🎥 Что вы хотите скачать?",
        "vid_btn": "🎥 Видео",
        "aud_btn": "🎵 Музыка (MP3)",
        "downloading": "⏳ Скачиваю файл, подождите...",
        "error": "❌ Не удалось скачать файл. Проверьте ссылку."
    }
}

user_lang = {}

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

async def check_subscription(bot: Bot, user_id: int) -> bool:
    if user_id == ADMIN_ID:
        return True
    try:
        member = await bot.get_chat_member(chat_id=REQUIRED_CHANNEL, user_id=user_id)
        if member.status in ["creator", "administrator", "member"]:
            return True
    except Exception as e:
        logging.error(f"Ошибка проверки подписки: {e}")
    return False

def get_language_keyboard():
    keyboard = []
    for code, data in translations.items():
        keyboard.append([InlineKeyboardButton(text=data["name"], callback_data=f"setlang_{code}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

async def start_handler(message: Message):
    await message.answer(
        "🌐 Пожалуйста выберите язык / Лутфан забонро интихоб кунед:",
        reply_markup=get_language_keyboard()
    )

async def set_language_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    lang_code = callback.data.split("_")[1]
    user_lang[user_id] = lang_code
    
    t = translations[lang_code]

    if not await check_subscription(bot, user_id):
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=t["sub_btn"], url=f"https://t.me/raqami_77")],
            [InlineKeyboardButton(text=t["check_btn"], callback_data="check_sub")]
        ])
        await callback.message.edit_text(f"{t['sub_text']} {REQUIRED_CHANNEL}", reply_markup=keyboard)
        return

    keyboard = [
        [InlineKeyboardButton(text="🌐 Изменить язык", callback_data="change_lang")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])

    await callback.message.edit_text(WELCOME_TEXT_CUSTOM, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

async def verify_subscription(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    lang = user_lang.get(user_id, "ru")
    t = translations[lang]

    if await check_subscription(bot, user_id):
        keyboard = [
            [InlineKeyboardButton(text="🌐 Изменить язык", callback_data="change_lang")]
        ]
        if user_id == ADMIN_ID:
            keyboard.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])

        await callback.message.edit_text(WELCOME_TEXT_CUSTOM, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    else:
        await callback.answer(t["not_sub"], show_alert=True)

async def change_lang_callback(callback: CallbackQuery):
    await callback.message.edit_text("🌐 Выберите язык / Лутфан забонро интихоб кунед:", reply_markup=get_language_keyboard())

async def admin_panel_callback(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔️ Доступ запрещен", show_alert=True)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"📢 Канал: {REQUIRED_CHANNEL}", callback_data="none")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ])
    await callback.message.edit_text("⚙️ **Админ-панель бота**\n\nОсновной канал для подписки настроен.", reply_markup=keyboard, parse_mode=ParseMode.MARKDOWN)

async def admin_back_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    keyboard = [
        [InlineKeyboardButton(text="🌐 Изменить язык", callback_data="change_lang")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    await callback.message.edit_text(WELCOME_TEXT_CUSTOM, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

async def url_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, "ru")
    t = translations[lang]

    if not await check_subscription(bot, user_id):
        await message.answer(t["not_sub"])
        return

    url = message.text.strip()
    if "youtube.com" in url or "youtu.be" in url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text=t["vid_btn"], callback_data=f"dl_vid:{url}"),
                InlineKeyboardButton(text=t["aud_btn"], callback_data=f"dl_aud:{url}")
            ]
        ])
        await message.answer(t["yt_choice"], reply_markup=keyboard)
    elif any(domain in url for domain in ["instagram.com", "tiktok.com", "pin.it", "pinterest.com"]):
        await message.answer(t["downloading"])
        await download_and_send_media(message, url, mode="video", lang=lang)
    else:
        await message.answer("⚠️ Пожалуйста, отправьте корректную ссылку.")

async def download_and_send_media(message: Message, url: str, mode: str = "video", lang: str = "ru"):
    t = translations[lang]
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
        await message.answer(t["error"])

async def youtube_callback_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = user_lang.get(user_id, "ru")
    t = translations[lang]
    
    data = callback.data
    action, url = data.split(":", 1)
    await callback.message.edit_text(t["downloading"])
    
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

    dp.message.register(start_handler, CommandStart())
    dp.callback_query.register(set_language_callback, F.data.startswith("setlang_"))
    dp.callback_query.register(verify_subscription, F.data == "check_sub")
    dp.callback_query.register(change_lang_callback, F.data == "change_lang")
    dp.callback_query.register(admin_panel_callback, F.data == "admin_panel")
    dp.callback_query.register(admin_back_callback, F.data == "admin_back")
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