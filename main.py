import asyncio
import json
import logging
import os
import sys
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

import yt_dlp
from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    FSInputFile
)

# ==================== 1. ОСНОВНЫЕ НАСТРОЙКИ И ПУТИ ====================
# Токен бота из переменных окружения Render
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Твой личный Telegram ID администратора
ADMIN_ID = 6051384649

# Папки и файлы для хранения данных
DOWNLOAD_DIR = Path("/tmp/tg_video_bot")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)

CONFIG_FILE = Path("bot_config.json")
# Проверяем cookies сначала в папке загрузки (если загрузили через бота), затем в корне проекта
COOKIES_TMP_PATH = DOWNLOAD_DIR / "cookies.txt"
COOKIES_ROOT_PATH = Path("cookies.txt")

# Пул из 4 потоков для быстрого параллельного скачивания видео
download_executor = ThreadPoolExecutor(max_workers=4)

# Настройки по умолчанию
default_config = {
    "channels": ["@raqami_77"],
    "welcome_text": (
        "👋 Привет! Я скоростной бот для скачивания видео.\n\n"
        "🔗 Отправь мне ссылку из:\n"
        "• YouTube (360p / 720p и MP3)\n"
        "• Instagram (Reels, посты и Stories)\n"
        "• TikTok (без водяных знаков)\n"
        "• Pinterest"
    ),
    "custom_buttons": [],
    "users": [],           # Список ID всех пользователей для статистики и рассылки
    "downloads_count": 0   # Счетчик успешных скачиваний
}

def load_config():
    """Загружает настройки и базу пользователей из файла"""
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                for k, v in default_config.items():
                    data.setdefault(k, v)
                return data
        except Exception as e:
            logging.error(f"Ошибка чтения конфига: {e}")
    return default_config.copy()

def save_config():
    """Сохраняет текущие настройки в файл"""
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(bot_config, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения конфига: {e}")

bot_config = load_config()

# Оперативная память для языков, коротких ссылок и мгновенного кэша файлов
user_lang = {}
url_storage = {}
file_cache = {}  # Кэш вида {"url|mode": {"file_id": "...", "title": "...", "type": "video/audio"}}

def get_active_cookies_path():
    """Проверяет, есть ли загруженный файл cookies.txt для Instagram Stories и YouTube"""
    if COOKIES_TMP_PATH.exists() and COOKIES_TMP_PATH.stat().st_size > 0:
        return str(COOKIES_TMP_PATH)
    if COOKIES_ROOT_PATH.exists() and COOKIES_ROOT_PATH.stat().st_size > 0:
        return str(COOKIES_ROOT_PATH)
    return None

# ==================== 2. СЛОВАРЬ ПЕРЕВОДОВ (4 ЯЗЫКА) ====================
translations = {
    "tg": {
        "name": "🇹🇯 Тоҷикӣ",
        "sub_text": "Салом! Барои истифодаи бот лутфан ба каналҳои мо обуна шавед:",
        "sub_btn": "📢 Обуна шудан",
        "check_btn": "✅ Ман обуна шудам",
        "not_sub": "❌ Шумо ҳанӯз ба ҳамаи каналҳо обуна нашудаед!",
        "yt_choice": "🎥 Сифати видео ё мусиқиро интихоб кунед:",
        "downloading": "⚡ Боргирии тез рафта истодааст...",
        "error": "❌ Боргирӣ нашуд. Шояд видео пӯшида аст, ҳаҷмаш аз 50 МБ зиёд аст ё барои Stories файли cookies лозим аст."
    },
    "uz": {
        "name": "🇺🇿 O'zbekcha",
        "sub_text": "Salom! Botdan foydalanish uchun kanallarimizga obuna bo'ling:",
        "sub_btn": "📢 Obuna bo'lish",
        "check_btn": "✅ Obuna bo'ldim",
        "not_sub": "❌ Siz hali barcha kanallarga obuna bo'lmadingiz!",
        "yt_choice": "🎥 Video sifatini yoki musiqani tanlang:",
        "downloading": "⚡ Tezkor yuklab olinmoqda...",
        "error": "❌ Yuklab bo'lmadi. Video yopiq bo'lishi yoki 50 MB dan katta bo'lishi mumkin."
    },
    "kk": {
        "name": "🇰🇿 Қазақша",
        "sub_text": "Сәлем! Ботты қолдану үшін арналарымызға жазылыңыз:",
        "sub_btn": "📢 Жазылу",
        "check_btn": "✅ Мен жазылдым",
        "not_sub": "❌ Сіз әлі барлық арналарға жазылған жоқсыз!",
        "yt_choice": "🎥 Бейне сапасын немесе музыканы таңдаңыз:",
        "downloading": "⚡ Жылдам жүктелуде...",
        "error": "❌ Жүктелмеді. Сілтемені тексеріңіз немесе файл 50 МБ-тан үлкен."
    },
    "ru": {
        "name": "🇷🇺 Русский",
        "sub_text": "Привет! Для использования бота подпишись на наши каналы:",
        "sub_btn": "📢 Подписаться",
        "check_btn": "✅ Я подписался",
        "not_sub": "❌ Вы еще не подписались на все каналы!",
        "yt_choice": "🎥 Выберите качество видео или аудио:",
        "downloading": "⚡ Быстрое скачивание, подождите пару секунд...",
        "error": "❌ Не удалось скачать. Проверьте ссылку (для Instagram Stories нужен загруженный в админке cookies.txt, а размер файла не должен превышать 50 МБ)."
    }
}

# ==================== 3. СОСТОЯНИЯ ДЛЯ АДМИН-ПАНЕЛИ ====================
class AdminStates(StatesGroup):
    waiting_for_new_channel = State()
    waiting_for_del_channel = State()
    waiting_for_welcome_text = State()
    waiting_for_new_button = State()
    waiting_for_broadcast = State()
    waiting_for_cookies = State()

# ==================== 4. ФОНОВЫЙ ВЕБ-СЕРВЕР ДЛЯ RENDER ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is alive and fast!")
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# ==================== 5. ПРОВЕРКА ПОДПИСКИ И КЛАВИАТУРЫ ====================
def register_user(user_id: int):
    """Сохраняет пользователя в базу при первом входе"""
    if user_id not in bot_config["users"]:
        bot_config["users"].append(user_id)
        save_config()

async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Проверяет подписку на обязательные каналы"""
    if user_id == ADMIN_ID or not bot_config["channels"]:
        return True
    for ch in bot_config["channels"]:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ["creator", "administrator", "member"]:
                return False
        except Exception as e:
            logging.warning(f"Канал {ch} недоступен для проверки (сделайте бота админом): {e}")
            continue
    return True

def get_language_keyboard():
    kb = [[InlineKeyboardButton(text=data["name"], callback_data=f"setlang_{code}")]
          for code, data in translations.items()]
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_main_menu_keyboard(user_id: int):
    kb = []
    for btn in bot_config.get("custom_buttons", []):
        kb.append([InlineKeyboardButton(text=btn["text"], url=btn["url"])])
    kb.append([InlineKeyboardButton(text="🌐 Изменить язык / Забон", callback_data="change_lang")])
    if user_id == ADMIN_ID:
        kb.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_subscribe_keyboard(lang: str):
    t = translations[lang]
    kb = []
    for ch in bot_config["channels"]:
        clean_ch = ch.replace("@", "").replace("https://t.me/", "")
        kb.append([InlineKeyboardButton(text=f"{t['sub_btn']} ({ch})", url=f"https://t.me/{clean_ch}")])
    kb.append([InlineKeyboardButton(text=t["check_btn"], callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==================== 6. СТАРТ И ВЫБОР ЯЗЫКА ====================
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    register_user(message.from_user.id)
    await message.answer(
        "🌐 Пожалуйста, выберите язык / Лутфан забонро интихоб кунед:",
        reply_markup=get_language_keyboard()
    )

async def set_language_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    register_user(user_id)
    lang_code = callback.data.split("_")[1]
    user_lang[user_id] = lang_code
    t = translations[lang_code]

    if not await check_subscription(bot, user_id):
        await callback.message.edit_text(t["sub_text"], reply_markup=get_subscribe_keyboard(lang_code))
        return

    await callback.message.edit_text(
        bot_config["welcome_text"],
        reply_markup=get_main_menu_keyboard(user_id)
    )

async def verify_subscription(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
    lang = user_lang.get(user_id, "ru")
    t = translations[lang]

    if await check_subscription(bot, user_id):
        await callback.message.edit_text(
            bot_config["welcome_text"],
            reply_markup=get_main_menu_keyboard(user_id)
        )
    else:
        await callback.answer(t["not_sub"], show_alert=True)

async def change_lang_callback(callback: CallbackQuery):
    await callback.message.edit_text(
        "🌐 Выберите язык / Лутфан забонро интихоб кунед:",
        reply_markup=get_language_keyboard()
    )

# ==================== 7. РАСШИРЕННАЯ АДМИН-ПАНЕЛЬ ====================
def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📊 Статистика", callback_data="adm_stats"),
         InlineKeyboardButton(text="📨 Рассылка всем", callback_data="adm_broadcast")],
        [InlineKeyboardButton(text="🍪 Загрузить cookies.txt (Stories)", callback_data="adm_cookies")],
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="adm_add_ch"),
         InlineKeyboardButton(text="➖ Удалить канал", callback_data="adm_del_ch")],
        [InlineKeyboardButton(text="🔓 Отключить обязат. подписку", callback_data="adm_clear_ch")],
        [InlineKeyboardButton(text="✏️ Изменить приветствие", callback_data="adm_edit_wel")],
        [InlineKeyboardButton(text="🔘 Добавить кнопку", callback_data="adm_add_btn"),
         InlineKeyboardButton(text="🗑 Удалить кнопки", callback_data="adm_clear_btn")],
        [InlineKeyboardButton(text="🧹 Очистить кэш и память", callback_data="adm_clear_cache")],
        [InlineKeyboardButton(text="🔙 Назад в главное меню", callback_data="adm_back")]
    ])

async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔️ Доступ только для администратора!", show_alert=True)
    await state.clear()

    channels_list = ", ".join(bot_config["channels"]) if bot_config["channels"] else "Отключена (свободный вход)"
    cookies_status = "✅ Подключен (Stories работают)" if get_active_cookies_path() else "❌ Не загружен"

    text = (
        "⚙️ <b>Панель управления ботом</b>\n\n"
        f"👥 <b>Пользователей в боте:</b> {len(bot_config['users'])}\n"
        f"📥 <b>Скачано файлов:</b> {bot_config['downloads_count']}\n"
        f"⚡ <b>Ссылок в быстром кэше:</b> {len(file_cache)}\n"
        f"📢 <b>Обязательная подписка:</b> {channels_list}\n"
        f"🍪 <b>Файл Cookies (Instagram/YT):</b> {cookies_status}\n"
        f"🔘 <b>Доп. кнопок:</b> {len(bot_config.get('custom_buttons', []))}\n\n"
        "Выберите действие:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())

async def admin_actions_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    action = callback.data

    if action == "adm_stats":
        await callback.answer(
            f"👥 Юзеров: {len(bot_config['users'])}\n"
            f"📥 Скачиваний: {bot_config['downloads_count']}\n"
            f"⚡ В кэше: {len(file_cache)}",
            show_alert=True
        )
    elif action == "adm_broadcast":
        await state.set_state(AdminStates.waiting_for_broadcast)
        await callback.message.edit_text(
            "📨 <b>Режим рассылки</b>\n\n"
            "Отправьте любое сообщение (текст, фото или видео), и бот разошлет его всем пользователям.\n"
            "Для отмены нажмите /start"
        )
    elif action == "adm_cookies":
        await state.set_state(AdminStates.waiting_for_cookies)
        await callback.message.edit_text(
            "🍪 <b>Загрузка cookies.txt для Instagram Stories и YouTube</b>\n\n"
            "Отправьте мне файл <code>cookies.txt</code> документом прямо в этот чат.\n"
            "Как только я его получу, бот сможет скачивать Instagram Stories и закрытые видео!\n\n"
            "Для отмены нажмите /start"
        )
    elif action == "adm_add_ch":
        await state.set_state(AdminStates.waiting_for_new_channel)
        await callback.message.edit_text(
            "📢 Отправьте юзернейм канала через @ (например: <code>@raqami_77</code>).\n"
            "⚠️ Обязательно добавьте бота в администраторы этого канала!"
        )
    elif action == "adm_del_ch":
        if not bot_config["channels"]:
            return await callback.answer("Список каналов уже пуст!", show_alert=True)
        await state.set_state(AdminStates.waiting_for_del_channel)
        ch_text = "\n".join(bot_config["channels"])
        await callback.message.edit_text(f"Отправьте юзернейм канала для удаления:\n{ch_text}")
    elif action == "adm_clear_ch":
        bot_config["channels"] = []
        save_config()
        await callback.answer("🔓 Обязательная подписка отключена!", show_alert=True)
        await admin_panel_callback(callback, state)
    elif action == "adm_edit_wel":
        await state.set_state(AdminStates.waiting_for_welcome_text)
        await callback.message.edit_text("✏️ Отправьте новый текст приветствия:")
    elif action == "adm_add_btn":
        await state.set_state(AdminStates.waiting_for_new_button)
        await callback.message.edit_text(
            "🔘 Отправьте название кнопки и ссылку через дефис.\n"
            "Пример:\n<code>Наш Инстаграм - https://instagram.com/hf_motion</code>"
        )
    elif action == "adm_clear_btn":
        bot_config["custom_buttons"] = []
        save_config()
        await callback.answer("✅ Дополнительные кнопки удалены!", show_alert=True)
        await admin_panel_callback(callback, state)
    elif action == "adm_clear_cache":
        file_cache.clear()
        url_storage.clear()
        for f in DOWNLOAD_DIR.glob("*"):
            if f.name != "cookies.txt":
                try:
                    f.unlink()
                except Exception:
                    pass
        await callback.answer("🧹 Память и кэш успешно очищены!", show_alert=True)
        await admin_panel_callback(callback, state)
    elif action == "adm_back":
        await state.clear()
        await callback.message.edit_text(
            bot_config["welcome_text"],
            reply_markup=get_main_menu_keyboard(callback.from_user.id)
        )

# Обработчики ввода данных от Админа
async def admin_cookies_msg(message: Message, state: FSMContext, bot: Bot):
    if message.document:
        file_info = await bot.get_file(message.document.file_id)
        await bot.download_file(file_info.file_path, destination=COOKIES_TMP_PATH)
        await state.clear()
        await message.answer(
            "✅ Файл <code>cookies.txt</code> успешно сохранен! Теперь Instagram Stories и YouTube работают с авторизацией.",
            reply_markup=get_admin_keyboard()
        )
    elif message.text and "Netscape" in message.text:
        with open(COOKIES_TMP_PATH, "w", encoding="utf-8") as f:
            f.write(message.text)
        await state.clear()
        await message.answer("✅ Текст cookies успешно сохранен!", reply_markup=get_admin_keyboard())
    else:
        await message.answer("❌ Пожалуйста, отправьте именно файл <code>cookies.txt</code> документом (или нажмите /start для отмены).")

async def admin_broadcast_msg(message: Message, state: FSMContext):
    await state.clear()
    users = bot_config.get("users", [])
    sent = 0
    status = await message.answer(f"⏳ Начинаю рассылку для {len(users)} пользователей...")
    for uid in users:
        try:
            await message.copy_to(chat_id=uid)
            sent += 1
            await asyncio.sleep(0.05)  # Защита от спам-блока Telegram
        except Exception:
            continue
    await status.edit_text(
        f"✅ Рассылка завершена!\nУспешно доставлено: <b>{sent}</b> из <b>{len(users)}</b>.",
        reply_markup=get_admin_keyboard()
    )

async def admin_add_channel_msg(message: Message, state: FSMContext):
    ch = message.text.strip()
    if not ch.startswith("@"):
        ch = "@" + ch.replace("https://t.me/", "")
    if ch not in bot_config["channels"]:
        bot_config["channels"].append(ch)
        save_config()
    await state.clear()
    await message.answer(f"✅ Канал {ch} добавлен!", reply_markup=get_admin_keyboard())

async def admin_del_channel_msg(message: Message, state: FSMContext):
    ch = message.text.strip()
    if ch in bot_config["channels"]:
        bot_config["channels"].remove(ch)
        save_config()
        await message.answer(f"✅ Канал {ch} удален!", reply_markup=get_admin_keyboard())
    else:
        await message.answer("❌ Такой канал не найден.", reply_markup=get_admin_keyboard())
    await state.clear()

async def admin_edit_welcome_msg(message: Message, state: FSMContext):
    bot_config["welcome_text"] = message.text
    save_config()
    await state.clear()
    await message.answer("✅ Приветствие обновлено!", reply_markup=get_admin_keyboard())

async def admin_add_button_msg(message: Message, state: FSMContext):
    if "-" not in message.text:
        return await message.answer("❌ Формат: Название кнопки - https://ссылка")
    name, url = message.text.split("-", 1)
    bot_config.setdefault("custom_buttons", []).append({"text": name.strip(), "url": url.strip()})
    save_config()
    await state.clear()
    await message.answer("✅ Кнопка добавлена!", reply_markup=get_admin_keyboard())

# ==================== 8. СКОРОСТНОЕ СКАЧИВАНИЕ ВИДЕО И STORIES ====================
async def url_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    register_user(user_id)
    lang = user_lang.get(user_id, "ru")
    t = translations[lang]

    if not await check_subscription(bot, user_id):
        await message.answer(t["sub_text"], reply_markup=get_subscribe_keyboard(lang))
        return

    url = message.text.strip()
    short_id = str(uuid.uuid4())[:8]
    url_storage[short_id] = url

    if "youtube.com" in url or "youtu.be" in url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⚡ 360p (Мгновенно)", callback_data=f"yt|360|{short_id}"),
                InlineKeyboardButton(text="🎬 720p (HD)", callback_data=f"yt|720|{short_id}")
            ],
            [
                InlineKeyboardButton(text="🎵 Скачать MP3 (Аудио)", callback_data=f"yt|mp3|{short_id}")
            ]
        ])
        await message.answer(t["yt_choice"], reply_markup=keyboard)
    elif any(d in url for d in ["instagram.com", "tiktok.com", "pin.it", "pinterest.com"]):
        status_msg = await message.answer(t["downloading"])
        await download_and_send_media(message, status_msg, url, mode="fast_video", lang=lang)
    else:
        await message.answer("⚠️ Пожалуйста, отправьте ссылку на YouTube, Instagram, TikTok или Pinterest.")

async def youtube_callback_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    lang = user_lang.get(user_id, "ru")
    t = translations[lang]

    _, quality, short_id = callback.data.split("|")
    url = url_storage.get(short_id)

    if not url:
        return await callback.message.edit_text("⚠️ Ссылка устарела, отправьте её заново.")

    await callback.message.edit_text(t["downloading"])
    await download_and_send_media(callback.message, callback.message, url, mode=quality, lang=lang)

async def download_and_send_media(message: Message, status_msg: Message, url: str, mode: str = "fast_video", lang: str = "ru"):
    t = translations[lang]
    cache_key = f"{url}|{mode}"

    # 1. ПРОВЕРКА МГНОВЕННОГО КЭША (отправка за 0.1 сек без скачивания)
    if cache_key in file_cache:
        cached = file_cache[cache_key]
        try:
            if cached["type"] == "audio":
                await message.answer_audio(audio=cached["file_id"], caption=cached["caption"])
            else:
                await message.answer_video(video=cached["file_id"], caption=cached["caption"])
            await status_msg.delete()
            return
        except Exception:
            file_cache.pop(cache_key, None)

    loop = asyncio.get_running_loop()
    unique_prefix = str(uuid.uuid4())[:8]

    # 2. НАСТРОЙКИ МАКСИМАЛЬНОЙ СКОРОСТИ YT-DLP
    ydl_opts = {
        'outtmpl': str(DOWNLOAD_DIR / f'{unique_prefix}_%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'nocheckcertificate': True,
        'concurrent_fragment_downloads': 8,  # Качаем в 8 параллельных потоков
        'buffersize': 1024 * 64,
        'http_chunk_size': 10485760,         # Блоки по 10 МБ против замедления YouTube
        'socket_timeout': 15,
        'retries': 3,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'
        }
    }

    # Если загружен cookies.txt — подключаем его (открывает доступ к Instagram Stories и YouTube)
    cookies_file = get_active_cookies_path()
    if cookies_file:
        ydl_opts['cookiefile'] = cookies_file

    # Выбираем готовые mp4-форматы, чтобы не тратить время процессора на склейку
    if mode == "mp3":
        ydl_opts.update({
            'format': 'bestaudio[filesize<50M]/bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '128',  # 128 kbps конвертируется в 2 раза быстрее
            }],
        })
    elif mode == "360":
        ydl_opts['format'] = 'best[height<=360][ext=mp4]/best[height<=480][ext=mp4]/best[ext=mp4]/best'
    elif mode == "720":
        ydl_opts['format'] = 'best[height<=720][ext=mp4][filesize<50M]/best[height<=720][ext=mp4]/best[ext=mp4]/best'
    else:
        # Для Instagram (Reels + Stories), TikTok и Pinterest
        ydl_opts['format'] = 'best[ext=mp4][filesize<50M]/best[ext=mp4]/best'

    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            # Если это сторис или карусель из нескольких элементов, берем первый/выбранный
            if 'entries' in info and info['entries']:
                info = info['entries'][0]
            filename = ydl.prepare_filename(info)
            if mode == "mp3":
                filename = str(Path(filename).with_suffix('.mp3'))
            return filename, info.get('title', 'Медиафайл')

    file_path = None
    try:
        file_path, title = await loop.run_in_executor(download_executor, download)

        if mode == "mp3":
            caption = f"🎵 {title[:100]}"
            sent_msg = await message.answer_audio(audio=FSInputFile(file_path), caption=caption)
            if sent_msg.audio:
                file_cache[cache_key] = {"file_id": sent_msg.audio.file_id, "caption": caption, "type": "audio"}
        else:
            caption = f"🎬 {title[:100]}"
            sent_msg = await message.answer_video(video=FSInputFile(file_path), caption=caption, supports_streaming=True)
            if sent_msg.video:
                file_cache[cache_key] = {"file_id": sent_msg.video.file_id, "caption": caption, "type": "video"}

        # Увеличиваем счетчик скачиваний в статистике
        bot_config["downloads_count"] = bot_config.get("downloads_count", 0) + 1
        save_config()

        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logging.error(f"Ошибка скачивания ({url}): {e}")
        await message.answer(t["error"])
    finally:
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

# ==================== 9. ЗАПУСК БОТА ====================
async def main():
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    if not BOT_TOKEN:
        logging.error("Не найден BOT_TOKEN!")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Основные команды
    dp.message.register(start_handler, CommandStart())
    dp.callback_query.register(set_language_callback, F.data.startswith("setlang_"))
    dp.callback_query.register(verify_subscription, F.data == "check_sub")
    dp.callback_query.register(change_lang_callback, F.data == "change_lang")

    # Обработчики Админ-панели
    dp.callback_query.register(admin_panel_callback, F.data == "admin_panel")
    dp.callback_query.register(admin_actions_callback, F.data.startswith("adm_"))
    dp.message.register(admin_cookies_msg, AdminStates.waiting_for_cookies)
    dp.message.register(admin_broadcast_msg, AdminStates.waiting_for_broadcast)
    dp.message.register(admin_add_channel_msg, AdminStates.waiting_for_new_channel)
    dp.message.register(admin_del_channel_msg, AdminStates.waiting_for_del_channel)
    dp.message.register(admin_edit_welcome_msg, AdminStates.waiting_for_welcome_text)
    dp.message.register(admin_add_button_msg, AdminStates.waiting_for_new_button)

    # Обработчики ссылок
    dp.callback_query.register(youtube_callback_handler, F.data.startswith("yt|"))
    dp.message.register(url_handler, F.text.startswith("http"))

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Скоростной бот успешно запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")