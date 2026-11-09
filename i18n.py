from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config.settings import settings

class UserLanguageStorage:
    def __init__(self, default_lang: str = "ru"):
        self.default_lang = default_lang
        self._user_langs: Dict[int, str] = {}

    def get_lang(self, user_id: int, telegram_lang_code: str = None) -> str:
        if user_id in self._user_langs:
            return self._user_langs[user_id]
        if telegram_lang_code and telegram_lang_code.lower().startswith("tg"):
            self._user_langs[user_id] = "tg"
            return "tg"
        return self.default_lang

    def set_lang(self, user_id: int, lang: str) -> None:
        if lang in ("ru", "tg"):
            self._user_langs[user_id] = lang

user_lang_storage = UserLanguageStorage(default_lang=settings.DEFAULT_LANGUAGE)

class I18nMiddleware(BaseMiddleware):
    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        lang = settings.DEFAULT_LANGUAGE
        if isinstance(event, (Message, CallbackQuery)) and event.from_user:
            lang = user_lang_storage.get_lang(event.from_user.id, event.from_user.language_code)
        data["lang"] = lang
        return await handler(event, data)
