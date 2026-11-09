import logging
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from config.settings import settings
from bot.locales.messages import get_msg
from bot.keyboards.inline import get_quality_keyboard, get_subscription_keyboard
from bot.services.platform_detector import Platform, PlatformDetector
from bot.services.downloader import get_downloader_for_platform, FileSizeExceededError
from bot.services.cleaner import file_cleaner
from bot.services.request_store import request_store
from bot.services.queue_manager import queue_manager
from bot.services.subscription import check_user_subscriptions

logger = logging.getLogger(__name__)
router = Router(name="video_router")

@router.message(F.text)
async def handle_potential_video_url(message: Message, bot: Bot, lang: str = "ru"):
    text = message.text or ""
    url = PlatformDetector.extract_first_url(text)
    if not url: return

    # Проверка подписки
    if not await check_user_subscriptions(bot, message.from_user.id):
        await message.answer(get_msg("sub_required", lang=lang), reply_markup=get_subscription_keyboard(lang=lang), parse_mode="HTML")
        return

    platform, cleaned_url = PlatformDetector.detect_platform(url)
    if platform == Platform.UNKNOWN or not cleaned_url:
        await message.answer(get_msg("unsupported_url", lang=lang), parse_mode="HTML")
        return

    status_msg = await message.answer(get_msg("status_processing", lang=lang), parse_mode="HTML")
    try:
        downloader = get_downloader_for_platform(platform)
        metadata = await downloader.extract_info(cleaned_url)
        req_id = request_store.save(message.from_user.id, cleaned_url, platform.value, metadata)
        prompt = get_msg("quality_select_prompt", lang=lang, title=metadata.title)
        kb = get_quality_keyboard(req_id, metadata.available_qualities, lang=lang)
        await status_msg.edit_text(prompt, reply_markup=kb, parse_mode="HTML")
    except Exception as e:
        await status_msg.edit_text(get_msg("error_generic", lang=lang, error=str(e)[:100]), parse_mode="HTML")

@router.callback_query(F.data.startswith("dl:"))
async def handle_quality_choice(callback: CallbackQuery, bot: Bot, lang: str = "ru"):
    parts = callback.data.split(":")
    if len(parts) < 3: return
    req_id, quality = parts[1], parts[2]
    pending = request_store.get(req_id)
    if not pending or callback.from_user.id != pending.user_id:
        await callback.answer("Expired or invalid", show_alert=True)
        return

    await callback.answer()
    await callback.message.edit_text(get_msg("status_downloading", lang=lang, quality=quality), parse_mode="HTML")

    async def task_runner():
        platform = Platform(pending.platform)
        downloader = get_downloader_for_platform(platform)
        with file_cleaner.create_task_dir() as task_dir:
            try:
                res = await downloader.download(pending.url, task_dir, quality)
                file_obj = FSInputFile(res.file_path)
                caption = get_msg("video_caption", lang=lang, title=res.title[:60], platform=res.platform, quality=res.quality, url=pending.url)
                try:
                    await bot.send_video(callback.message.chat.id, video=file_obj, caption=caption, parse_mode="HTML")
                except Exception:
                    await bot.send_document(callback.message.chat.id, document=file_obj, caption=caption, parse_mode="HTML")
                try: await bot.delete_message(callback.message.chat.id, callback.message.message_id)
                except Exception: pass
            except FileSizeExceededError:
                await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=get_msg("error_file_too_large", lang=lang), parse_mode="HTML")
            except Exception as e:
                await bot.edit_message_text(chat_id=callback.message.chat.id, message_id=callback.message.message_id, text=get_msg("error_generic", lang=lang, error=str(e)[:100]), parse_mode="HTML")

    try:
        await queue_manager.enqueue(req_id, pending.user_id, task_runner)
    except Exception:
        await callback.message.edit_text(get_msg("already_processing", lang=lang), parse_mode="HTML")
    finally:
        request_store.delete(req_id)
