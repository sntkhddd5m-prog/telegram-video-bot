import time
from typing import Any, Awaitable, Callable, Dict
from aiogram import BaseMiddleware
from aiogram.types import TelegramObject, Message, CallbackQuery
from config.settings import settings
from bot.locales.messages import get_msg

class RateLimitMiddleware(BaseMiddleware):
    def __init__(self, limit_seconds: float = settings.RATE_LIMIT_SECONDS):
        super().__init__()
        self.limit_seconds = limit_seconds
        self.last_user_times: Dict[int, float] = {}

    async def __call__(self, handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]], event: TelegramObject, data: Dict[str, Any]) -> Any:
        user_id = event.from_user.id if isinstance(event, (Message, CallbackQuery)) and event.from_user else None
        if user_id:
            now = time.time()
            if now - self.last_user_times.get(user_id, 0.0) < self.limit_seconds:
                lang = data.get("lang", settings.DEFAULT_LANGUAGE)
                if isinstance(event, Message):
                    await event.answer(get_msg("rate_limited", lang=lang, seconds=2))
                elif isinstance(event, CallbackQuery):
                    await event.answer(get_msg("rate_limited", lang=lang, seconds=2), show_alert=True)
                return
            self.last_user_times[user_id] = now
        return await handler(event, data)
