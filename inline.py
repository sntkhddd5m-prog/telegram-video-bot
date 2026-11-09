from typing import List
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from bot.locales.messages import get_msg
from config.settings import settings

def get_language_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
            InlineKeyboardButton(text="🇹🇯 Тоҷикӣ", callback_data="set_lang:tg"),
        ]
    ])

def get_subscription_keyboard(lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    for ch in settings.REQUIRED_CHANNELS:
        username = ch.lstrip('@')
        rows.append([InlineKeyboardButton(text=get_msg("btn_subscribe", lang), url=f"https://t.me/{username}")])
    rows.append([InlineKeyboardButton(text=get_msg("btn_check_sub", lang), callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def get_quality_keyboard(req_id: str, available_qualities: List[str], lang: str = "ru") -> InlineKeyboardMarkup:
    rows = []
    labels = {
        "360p": get_msg("quality_360", lang),
        "720p": get_msg("quality_720", lang),
        "1080p": get_msg("quality_1080", lang),
        "best": get_msg("quality_best", lang),
    }
    order = ["360p", "720p", "1080p", "best"]
    current_row = []
    for q in order:
        if q in available_qualities or q == "best":
            current_row.append(InlineKeyboardButton(text=labels.get(q, q), callback_data=f"dl:{req_id}:{q}"))
            if len(current_row) == 2:
                rows.append(current_row)
                current_row = []
    if current_row:
        rows.append(current_row)
    rows.append([InlineKeyboardButton(text=get_msg("cancel", lang), callback_data=f"cancel:{req_id}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)
