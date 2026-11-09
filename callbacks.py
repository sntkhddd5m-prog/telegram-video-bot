from aiogram import Router, F
from aiogram.types import CallbackQuery
from bot.locales.messages import get_msg
from bot.middlewares.i18n import user_lang_storage
from bot.keyboards.reply import get_main_menu_keyboard
from bot.services.request_store import request_store
from bot.services.subscription import check_user_subscriptions

router = Router(name="callbacks_router")

@router.callback_query(F.data.startswith("set_lang:"))
async def callback_set_language(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    if lang in ("ru", "tg"):
        user_lang_storage.set_lang(callback.from_user.id, lang)
    try: await callback.message.delete()
    except Exception: pass
    await callback.message.answer(get_msg("lang_changed", lang=lang), reply_markup=get_main_menu_keyboard(lang=lang), parse_mode="HTML")
    await callback.answer()

@router.callback_query(F.data == "check_sub")
async def callback_check_subscription(callback: CallbackQuery, lang: str = "ru"):
    is_sub = await check_user_subscriptions(callback.bot, callback.from_user.id)
    if is_sub:
        try: await callback.message.delete()
        except Exception: pass
        await callback.message.answer(get_msg("welcome", lang=lang), reply_markup=get_main_menu_keyboard(lang=lang), parse_mode="HTML")
    else:
        await callback.answer(get_msg("sub_not_passed", lang=lang), show_alert=True)

@router.callback_query(F.data.startswith("cancel:"))
async def callback_cancel_request(callback: CallbackQuery, lang: str = "ru"):
    req_id = callback.data.split(":")[1]
    request_store.delete(req_id)
    try: await callback.message.edit_text(get_msg("cancelled", lang=lang), reply_markup=None)
    except Exception: pass
    await callback.answer(get_msg("cancelled", lang=lang))
