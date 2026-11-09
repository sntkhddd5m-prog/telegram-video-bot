from aiogram import Bot
from config.settings import settings

async def check_user_subscriptions(bot: Bot, user_id: int) -> bool:
    if not settings.REQUIRED_CHANNELS:
        return True

    for channel in settings.REQUIRED_CHANNELS:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status not in ["member", "administrator", "creator"]:
                return False
        except Exception as e:
            print(f"Ошибка проверки подписки для {channel}: {e}")
            return False
    return True
