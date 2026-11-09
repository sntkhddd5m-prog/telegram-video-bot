from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from bot.locales.messages import get_msg

def get_main_menu_keyboard(lang: str = "ru") -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=get_msg("menu_button_help", lang)), KeyboardButton(text=get_msg("menu_button_lang", lang))],
            [KeyboardButton(text=get_msg("menu_button_status", lang))],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )
