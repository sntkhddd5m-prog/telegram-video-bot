import asyncio
import json
import logging
import os
import sys
import threading
import uuid
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

# ==================== ОСНОВНЫЕ НАСТРОЙКИ ====================
# Токен берется автоматически из настроек Render (Environment Variables)
BOT_TOKEN = os.getenv("BOT_TOKEN")

# Твой личный Telegram ID администратора (можно изменить при необходимости)
ADMIN_ID = 6051384649

# Папка для временного хранения скачанных видео и файл настроек
DOWNLOAD_DIR = Path("/tmp/tg_video_bot")
DOWNLOAD_DIR.mkdir(parents=True, exist_ok=True)
CONFIG_FILE = Path("bot_config.json")

# Настройки по умолчанию (сохраняются и меняются через Админ-панель)
default_config = {
    "channels": ["@raqami_77"],
    "welcome_text": (
        "👋 Привет! Я быстрый бот для скачивания видео.\n\n"
        "🔗 Отправь мне ссылку из:\n"
        "• YouTube (выбор качества 360p / 720p и MP3)\n"
        "• Instagram (Reels и посты)\n"
        "• TikTok (без водяных знаков)\n"
        "• Pinterest"
    ),
    "custom_buttons": []  # Список дополнительных кнопок вида [{"text": "Наш чат", "url": "https://t.me/..."}]
}

# Функция загрузки настроек из файла
def load_config():
    if CONFIG_FILE.exists():
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logging.error(f"Ошибка чтения конфига: {e}")
    return default_config.copy()

# Функция сохранения настроек в файл
def save_config(cfg):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, ensure_ascii=False, indent=2)
    except Exception as e:
        logging.error(f"Ошибка сохранения конфига: {e}")

bot_config = load_config()

# Память для выбранных языков и коротких ID ссылок (чтобы кнопки YouTube не ломались)
user_lang = {}
url_storage = {}

# ==================== ПЕРЕВОДЫ ИНТЕРФЕЙСА ====================
translations = {
    "tg": {
        "name": "🇹🇯 Тоҷикӣ",
        "sub_text": "Салом! Барои истифодаи бот лутфан ба каналҳои мо обуна шавед:",
        "sub_btn": "📢 Обуна шудан",
        "check_btn": "✅ Ман обуна шудам",
        "not_sub": "❌ Шумо ҳанӯз ба ҳамаи каналҳо обуна нашудаед!",
        "yt_choice": "🎥 Сифати видео ё мусиқиро интихоб кунед:",
        "downloading": "⏳ Боргирӣ рафта истодааст, лутфан каме интизор шавед...",
        "error": "❌ Хатогӣ! Истинод нодуруст аст ё видео пӯшида аст (масалан, Stories бе кукиҳо дастрас нест)."
    },
    "uz": {
        "name": "🇺🇿 O'zbekcha",
        "sub_text": "Salom! Botdan foydalanish uchun kanallarimizga obuna bo'ling:",
        "sub_btn": "📢 Obuna bo'lish",
        "check_btn": "✅ Obuna bo'ldim",
        "not_sub": "❌ Siz hali barcha kanallarga obuna bo'lmadingiz!",
        "yt_choice": "🎥 Video sifatini yoki musiqani tanlang:",
        "downloading": "⏳ Yuklab olinmoqda, iltimos biroz kuting...",
        "error": "❌ Xatolik! Havola noto'g'ri yoki video yopiq."
    },
    "kk": {
        "name": "🇰🇿 Қазақша",
        "sub_text": "Сәлем! Ботты қолдану үшін арналарымызға жазылыңыз:",
        "sub_btn": "📢 Жазылу",
        "check_btn": "✅ Мен жазылдым",
        "not_sub": "❌ Сіз әлі барлық арналарға жазылған жоқсыз!",
        "yt_choice": "🎥 Бейне сапасын немесе музыканы таңдаңыз:",
        "downloading": "⏳ Жүктелуде, сәл күте тұрыңыз...",
        "error": "❌ Қате! Сілтемені тексеріңіз."
    },
    "ru": {
        "name": "🇷🇺 Русский",
        "sub_text": "Привет! Для использования бота подпишись на наши каналы:",
        "sub_btn": "📢 Подписаться",
        "check_btn": "✅ Я подписался",
        "not_sub": "❌ Вы еще не подписались на все каналы!",
        "yt_choice": "🎥 Выберите качество видео или аудио:",
        "downloading": "⏳ Скачиваю файл, подождите пару секунд...",
        "error": "❌ Не удалось скачать. Возможно, аккаунт закрыт, это Instagram Stories (требует авторизации) или видео больше 50 МБ."
    }
}

# ==================== СОСТОЯНИЯ ДЛЯ АДМИН-ПАНЕЛИ ====================
class AdminStates(StatesGroup):
    waiting_for_new_channel = State()
    waiting_for_del_channel = State()
    waiting_for_welcome_text = State()
    waiting_for_new_button = State()

# ==================== ВЕБ-СЕРВЕР ДЛЯ RENDER ====================
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is running!")
    def log_message(self, format, *args):
        pass

def run_web_server():
    port = int(os.getenv("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    server.serve_forever()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def check_subscription(bot: Bot, user_id: int) -> bool:
    """Проверяет подписку пользователя на все каналы из списка"""
    if user_id == ADMIN_ID:
        return True  # Админа пускаем всегда
    for ch in bot_config["channels"]:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status not in ["creator", "administrator", "member"]:
                return False
        except Exception as e:
            logging.warning(f"Не удалось проверить канал {ch} (бот должен быть админом канала): {e}")
            # Если бот еще не админ в канале, не блокируем работу намертво
            continue
    return True

def get_language_keyboard():
    """Клавиатура выбора языка"""
    kb = []
    for code, data in translations.items():
        kb.append([InlineKeyboardButton(text=data["name"], callback_data=f"setlang_{code}")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_main_menu_keyboard(user_id: int):
    """Клавиатура главного меню (с кастомными кнопками и админкой)"""
    kb = []
    # Добавляем кнопки, которые создал админ
    for btn in bot_config.get("custom_buttons", []):
        kb.append([InlineKeyboardButton(text=btn["text"], url=btn["url"])])
    
    kb.append([InlineKeyboardButton(text="🌐 Изменить язык / Забон", callback_data="change_lang")])
    if user_id == ADMIN_ID:
        kb.append([InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="admin_panel")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

def get_subscribe_keyboard(lang: str):
    """Клавиатура со ссылками на каналы для подписки"""
    t = translations[lang]
    kb = []
    for ch in bot_config["channels"]:
        clean_ch = ch.replace("@", "").replace("https://t.me/", "")
        kb.append([InlineKeyboardButton(text=f"{t['sub_btn']} ({ch})", url=f"https://t.me/{clean_ch}")])
    kb.append([InlineKeyboardButton(text=t["check_btn"], callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

# ==================== ОБРАБОТЧИКИ КОМАНД И МЕНЮ ====================
async def start_handler(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "🌐 Пожалуйста, выберите язык / Лутфан забонро интихоб кунед:",
        reply_markup=get_language_keyboard()
    )

async def set_language_callback(callback: CallbackQuery, bot: Bot):
    user_id = callback.from_user.id
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

# ==================== РАБОЧАЯ АДМИН-ПАНЕЛЬ ====================
def get_admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить канал", callback_data="adm_add_ch"),
         InlineKeyboardButton(text="➖ Удалить канал", callback_data="adm_del_ch")],
        [InlineKeyboardButton(text="✏️ Изменить приветствие", callback_data="adm_edit_wel")],
        [InlineKeyboardButton(text="🔘 Добавить кнопку-ссылку", callback_data="adm_add_btn"),
         InlineKeyboardButton(text="🗑 Очистить кнопки", callback_data="adm_clear_btn")],
        [InlineKeyboardButton(text="🔙 Назад в меню", callback_data="adm_back")]
    ])

async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return await callback.answer("⛔️ Доступ запрещен", show_alert=True)
    await state.clear()
    
    channels_list = ", ".join(bot_config["channels"]) if bot_config["channels"] else "Нет каналов"
    btns_count = len(bot_config.get("custom_buttons", []))
    
    text = (
        "⚙️ <b>Панель администратора</b>\n\n"
        f"📢 <b>Каналы подписки:</b> {channels_list}\n"
        f"🔘 <b>Доп. кнопок в меню:</b> {btns_count}\n\n"
        "Выберите нужное действие кнопками ниже:"
    )
    await callback.message.edit_text(text, reply_markup=get_admin_keyboard())

async def admin_actions_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    action = callback.data

    if action == "adm_add_ch":
        await state.set_state(AdminStates.waiting_for_new_channel)
        await callback.message.edit_text(
            "📢 Отправьте юзернейм нового канала через @ (например: <code>@raqami_77</code>).\n"
            "⚠️ Не забудьте сделать бота администратором в этом канале!"
        )
    elif action == "adm_del_ch":
        if not bot_config["channels"]:
            return await callback.answer("Список каналов пуст!", show_alert=True)
        await state.set_state(AdminStates.waiting_for_del_channel)
        ch_text = "\n".join(bot_config["channels"])
        await callback.message.edit_text(f"Отправьте юзернейм канала, который нужно удалить:\n{ch_text}")
    elif action == "adm_edit_wel":
        await state.set_state(AdminStates.waiting_for_welcome_text)
        await callback.message.edit_text("✏️ Отправьте новый текст приветствия одним сообщением:")
    elif action == "adm_add_btn":
        await state.set_state(AdminStates.waiting_for_new_button)
        await callback.message.edit_text(
            "🔘 Отправьте название кнопки и ссылку через дефис.\n"
            "Пример:\n<code>Мой Инстаграм - https://instagram.com/hf_motion</code>"
        )
    elif action == "adm_clear_btn":
        bot_config["custom_buttons"] = []
        save_config(bot_config)
        await callback.answer("✅ Все дополнительные кнопки удалены!", show_alert=True)
        await admin_panel_callback(callback, state)
    elif action == "adm_back":
        await state.clear()
        await callback.message.edit_text(
            bot_config["welcome_text"],
            reply_markup=get_main_menu_keyboard(callback.from_user.id)
        )

# Прием текста от админа для настроек
async def admin_add_channel_msg(message: Message, state: FSMContext):
    ch = message.text.strip()
    if not ch.startswith("@"):
        ch = "@" + ch.replace("https://t.me/", "")
    if ch not in bot_config["channels"]:
        bot_config["channels"].append(ch)
        save_config(bot_config)
    await state.clear()
    await message.answer(f"✅ Канал {ch} успешно добавлен!", reply_markup=get_admin_keyboard())

async def admin_del_channel_msg(message: Message, state: FSMContext):
    ch = message.text.strip()
    if ch in bot_config["channels"]:
        bot_config["channels"].remove(ch)
        save_config(bot_config)
        await message.answer(f"✅ Канал {ch} удален!", reply_markup=get_admin_keyboard())
    else:
        await message.answer("❌ Такой канал не найден в списке.", reply_markup=get_admin_keyboard())
    await state.clear()

async def admin_edit_welcome_msg(message: Message, state: FSMContext):
    bot_config["welcome_text"] = message.text
    save_config(bot_config)
    await state.clear()
    await message.answer("✅ Приветствие успешно обновлено!", reply_markup=get_admin_keyboard())

async def admin_add_button_msg(message: Message, state: FSMContext):
    if "-" not in message.text:
        return await message.answer("❌ Ошибка формата. Напишите через дефис: Текст - https://ссылка")
    name, url = message.text.split("-", 1)
    bot_config.setdefault("custom_buttons", []).append({"text": name.strip(), "url": url.strip()})
    save_config(bot_config)
    await state.clear()
    await message.answer("✅ Кнопка добавлена!", reply_markup=get_admin_keyboard())

# ==================== СКАЧИВАНИЕ ВИДЕО И АУДИО ====================
async def url_handler(message: Message, bot: Bot):
    user_id = message.from_user.id
    lang = user_lang.get(user_id, "ru")
    t = translations[lang]

    if not await check_subscription(bot, user_id):
        await message.answer(t["sub_text"], reply_markup=get_subscribe_keyboard(lang))
        return

    url = message.text.strip()

    # Сохраняем ссылку под коротким 8-значным кодом, чтобы не превышать лимит кнопок Telegram
    short_id = str(uuid.uuid4())[:8]
    url_storage[short_id] = url

    if "youtube.com" in url or "youtu.be" in url:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🎥 360p (Быстро)", callback_data=f"yt|360|{short_id}"),
                InlineKeyboardButton(text="🎥 720p (HD)", callback_data=f"yt|720|{short_id}")
            ],
            [
                InlineKeyboardButton(text="🎵 Скачать MP3 (Музыка)", callback_data=f"yt|mp3|{short_id}")
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
        return await callback.message.edit_text("⚠️ Ссылка устарела, отправьте её еще раз.")

    await callback.message.edit_text(t["downloading"])
    await download_and_send_media(callback.message, callback.message, url, mode=quality, lang=lang)

async def download_and_send_media(message: Message, status_msg: Message, url: str, mode: str = "fast_video", lang: str = "ru"):
    t = translations[lang]
    loop = asyncio.get_running_loop()
    unique_prefix = str(uuid.uuid4())[:8]

    # Оптимизированные настройки yt-dlp для быстрой загрузки на Render
    ydl_opts = {
        'outtmpl': str(DOWNLOAD_DIR / f'{unique_prefix}_%(id)s.%(ext)s'),
        'noplaylist': True,
        'quiet': True,
        'no_warnings': True,
        'geo_bypass': True,
        'concurrent_fragment_downloads': 4,  # Ускоряет скачивание в 4 потока
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }

    # Подбор формата без тяжелой перекодировки процессором
    if mode == "mp3":
        ydl_opts.update({
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })
    elif mode == "360":
        ydl_opts['format'] = 'best[height<=360][ext=mp4]/best[height<=360]/best[ext=mp4]/best'
    elif mode == "720":
        ydl_opts['format'] = 'best[height<=720][ext=mp4]/best[height<=720]/best[ext=mp4]/best'
    else:
        # Для TikTok, Instagram, Pinterest берем сразу готовый mp4 файл до 50 МБ
        ydl_opts['format'] = 'best[ext=mp4][filesize<50M]/best[ext=mp4]/best'

    def download():
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if mode == "mp3":
                filename = str(Path(filename).with_suffix('.mp3'))
            return filename, info.get('title', 'Видео')

    file_path = None
    try:
        file_path, title = await loop.run_in_executor(None, download)

        if mode == "mp3":
            await message.answer_audio(audio=FSInputFile(file_path), caption=f"🎵 {title[:100]}")
        else:
            await message.answer_video(video=FSInputFile(file_path), caption=f"🎬 {title[:100]}")

        # Удаляем сообщение "Скачиваю..." после успешной отправки
        try:
            await status_msg.delete()
        except Exception:
            pass

    except Exception as e:
        logging.error(f"Ошибка скачивания ({url}): {e}")
        await message.answer(t["error"])
    finally:
        # Всегда очищаем скачанный файл с сервера, чтобы память Render не переполнилась
        if file_path and os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass

# ==================== ЗАПУСК БОТА ====================
async def main():
    # Запускаем фоновый веб-сервер для Render
    server_thread = threading.Thread(target=run_web_server, daemon=True)
    server_thread.start()

    if not BOT_TOKEN:
        logging.error("Не задан BOT_TOKEN!")
        sys.exit(1)

    bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=MemoryStorage())

    # Регистрация команд и кнопок
    dp.message.register(start_handler, CommandStart())
    dp.callback_query.register(set_language_callback, F.data.startswith("setlang_"))
    dp.callback_query.register(verify_subscription, F.data == "check_sub")
    dp.callback_query.register(change_lang_callback, F.data == "change_lang")

    # Регистрация обработчиков Админ-панели
    dp.callback_query.register(admin_panel_callback, F.data == "admin_panel")
    dp.callback_query.register(admin_actions_callback, F.data.startswith("adm_"))
    dp.message.register(admin_add_channel_msg, AdminStates.waiting_for_new_channel)
    dp.message.register(admin_del_channel_msg, AdminStates.waiting_for_del_channel)
    dp.message.register(admin_edit_welcome_msg, AdminStates.waiting_for_welcome_text)
    dp.message.register(admin_add_button_msg, AdminStates.waiting_for_new_button)

    # Регистрация скачивания по ссылкам
    dp.callback_query.register(youtube_callback_handler, F.data.startswith("yt|"))
    dp.message.register(url_handler, F.text.startswith("http"))

    await bot.delete_webhook(drop_pending_updates=True)
    logging.info("Бот полностью готов к работе!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logging.info("Бот остановлен.")