from typing import Dict, Any

MESSAGES: Dict[str, Dict[str, str]] = {
    "ru": {
        "welcome": (
            "👋 <b>Привет! Я бот для скачивания видео.</b>\n\n"
            "📥 Отправь мне ссылку на видео из:\n"
            "• <b>YouTube</b> (видео и Shorts)\n"
            "• <b>Instagram</b> (Reels и посты)\n"
            "• <b>TikTok</b> (видеоролики)\n"
            "• <b>Pinterest</b> (видео-пины)\n\n"
            "⚡️ <i>Лимит размера: до 50 МБ (ограничение Telegram Bot API).</i>\n"
            "🌐 Используй кнопки ниже для смены языка или получения помощи."
        ),
        "help": (
            "📖 <b>Инструкция по использованию:</b>\n\n"
            "1. Подпишись на обязательный канал.\n"
            "2. Скопируй ссылку на видео и отправь в этот чат.\n"
            "3. Выбери качество и получи файл!"
        ),
        "lang_choose": "🌐 <b>Выберите язык интерфейса:</b>",
        "lang_changed": "✅ Язык успешно изменён на <b>Русский</b>.",
        "menu_button_help": "ℹ️ Помощь",
        "menu_button_lang": "🌐 Сменить язык",
        "menu_button_status": "📊 Статус",
        "status_info": "📊 <b>Статус:</b> Всё работает стабильно!",
        "unsupported_url": "❌ <b>Ссылка не поддерживается!</b>",
        "quality_select_prompt": "🎬 <b>Видео найдено:</b> <i>{title}</i>\nВыберите качество:",
        "quality_360": "📱 360p",
        "quality_720": "🎬 720p",
        "quality_1080": "🖥 1080p",
        "quality_best": "⚡️ Авто",
        "cancel": "❌ Отмена",
        "cancelled": "🚫 Действие отменено.",
        "queue_position": "⏳ Вы в очереди. Позиция: <b>{position}</b>...",
        "status_processing": "🔍 <b>Обработка ссылки...</b>",
        "status_downloading": "📥 <b>Загрузка ({quality})...</b>",
        "status_sending": "📤 <b>Отправка в Telegram...</b>",
        "error_file_too_large": "⚠️ <b>Файл больше 50 МБ!</b> Выберите качество ниже.",
        "error_private_or_not_found": "🔒 <b>Видео недоступно или скрыто.</b>",
        "error_platform_blocked": "🚫 <b>Платформа ограничила доступ.</b>",
        "error_drm_protected": "🛡 <b>Видео защищено DRM.</b>",
        "error_timeout": "⏱ <b>Время ожидания истекло.</b>",
        "error_generic": "❌ <b>Ошибка:</b> <code>{error}</code>",
        "rate_limited": "⏳ Подождите {seconds} сек.",
        "already_processing": "⚠️ У вас уже есть активная загрузка.",
        "video_caption": "🎬 <b>{title}</b>\n🔗 <a href='{url}'>{platform}</a> | <code>{quality}</code>",
        "sub_required": (
            "⚠️ <b>Для использования бота необходимо подписаться на наши каналы!</b>\n\n"
            "Пожалуйста, подпишитесь на каналы ниже, а затем нажмите кнопку проверки:"
        ),
        "btn_subscribe": "📢 Подписаться на канал",
        "btn_check_sub": "🔄 Проверить подписку",
        "sub_not_passed": "❌ Вы подписались не на все каналы. Проверьте подписки и нажмите кнопку еще раз."
    },
    "tg": {
        "welcome": (
            "👋 <b>Салом! Ман бот барои боргирии видео ҳастам.</b>\n\n"
            "📥 Истиноди видеоро фиристед (YouTube, Instagram, TikTok, Pinterest)."
        ),
        "help": "📖 <b>Роҳнамо:</b> Ба каналҳо обуна шавед ва истинод фиристед.",
        "lang_choose": "🌐 <b>Забонро интихоб кунед:</b>",
        "lang_changed": "✅ Забон ба <b>Тоҷикӣ</b> иваз шуд.",
        "menu_button_help": "ℹ️ Роҳнамо",
        "menu_button_lang": "🌐 Ивази забон",
        "menu_button_status": "📊 Вазъ",
        "status_info": "📊 <b>Вазъ:</b> Ҳамааш кор мекунад!",
        "unsupported_url": "❌ <b>Истинод дастгирӣ намешавад!</b>",
        "quality_select_prompt": "🎬 <b>Видео ёфт шуд:</b> <i>{title}</i>\nСифатро интихоб кунед:",
        "quality_360": "📱 360p",
        "quality_720": "🎬 720p",
        "quality_1080": "🖥 1080p",
        "quality_best": "⚡️ Худкор",
        "cancel": "❌ Бекор кардан",
        "cancelled": "🚫 Бекор карда шуд.",
        "queue_position": "⏳ Мавқеъ дар навбат: <b>{position}</b>...",
        "status_processing": "🔍 <b>Коркарди истинод...</b>",
        "status_downloading": "📥 <b>Боргирӣ ({quality})...</b>",
        "status_sending": "📤 <b>Ирсол ба Telegram...</b>",
        "error_file_too_large": "⚠️ <b>Файл аз 50 МБ калонтар аст!</b>",
        "error_private_or_not_found": "🔒 <b>Видео дастнорас аст.</b>",
        "error_platform_blocked": "🚫 <b>Дастрасӣ маҳдуд аст.</b>",
        "error_drm_protected": "🛡 <b>Муҳофизат шудааст.</b>",
        "error_timeout": "⏱ <b>Вақт ба охир расид.</b>",
        "error_generic": "❌ <b>Хатогӣ:</b> <code>{error}</code>",
        "rate_limited": "⏳ {seconds} сония интизор шавед.",
        "already_processing": "⚠️ Шумо аллакай боргирӣ доред.",
        "video_caption": "🎬 <b>{title}</b>\n🔗 <a href='{url}'>{platform}</a> | <code>{quality}</code>",
        "sub_required": (
            "⚠️ <b>Барои истифодаи бот бояд ба каналҳои мо обуна шавед!</b>\n\n"
            "Лутфан ба каналҳои зерин обуна шуда, тугмаро пахш кунед:"
        ),
        "btn_subscribe": "📢 Обуна шудан ба канал",
        "btn_check_sub": "🔄 Санҷидани обуна",
        "sub_not_passed": "❌ Шумо ба ҳамаи каналҳо обуна нашудаед."
    }
}

def get_msg(key: str, lang: str = "ru", **kwargs: Any) -> str:
    lang_dict = MESSAGES.get(lang, MESSAGES["ru"])
    template = lang_dict.get(key, MESSAGES["ru"].get(key, key))
    if kwargs:
        try:
            return template.format(**kwargs)
        except Exception:
            return template
    return template
