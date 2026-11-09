from aiogram import Router, F
from aiogram.filters import CommandStart, Command
from aiogram.types import Message
from bot.locales.messages import get_msg, MESSAGES
from bot.keyboards.reply import get_main_menu_keyboard
from bot.keyboards.inline import get_language_keyboard

router = Router(name="commands_router")

@router.message(CommandStart())
async def cmd_start(message: Message, lang: str = "ru"):
    await message.answer(get_msg("welcome", lang=lang), reply_markup=get_main_menu_keyboard(lang=lang), parse_mode="HTML")

@router.message(Command("help"))
async def cmd_help(message: Message, lang: str = "ru"):
    await message.answer(get_msg("help", lang=lang), parse_mode="HTML")

@router.message(Command("lang"))
async def cmd_lang(message: Message, lang: str = "ru"):
    await message.answer(get_msg("lang_choose", lang=lang), reply_markup=get_language_keyboard(), parse_mode="HTML")

@router.message(Command("status"))
async def cmd_status(message: Message, lang: str = "ru"):
    await message.answer(get_msg("status_info", lang=lang), parse_mode="HTML")

@router.message(F.text.in_([MESSAGES["ru"]["menu_button_help"], MESSAGES["tg"]["menu_button_help"]]))
async def btn_help(message: Message, lang: str = "ru"): await cmd_help(message, lang)

@router.message(F.text.in_([MESSAGES["ru"]["menu_button_lang"], MESSAGES["tg"]["menu_button_lang"]]))
async def btn_lang(message: Message, lang: str = "ru"): await cmd_lang(message, lang)

@router.message(F.text.in_([MESSAGES["ru"]["menu_button_status"], MESSAGES["tg"]["menu_button_status"]]))
async def btn_status(message: Message, lang: str = "ru"): await cmd_status(message, lang)
