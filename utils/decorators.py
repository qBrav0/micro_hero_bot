from functools import wraps
from typing import Callable, Any
from aiogram import types
import logging

logger = logging.getLogger(__name__)


def admin_only(func: Callable) -> Callable:
    """Декоратор для обмеження доступу тільки для адміністраторів"""
    @wraps(func)
    async def wrapper(message_or_callback: Any, *args, **kwargs):
        # Перезавантажуємо ADMIN_IDS для отримання актуального списку
        import config
        import importlib
        importlib.reload(config)
        ADMIN_IDS = config.ADMIN_IDS
        
        user_id = None
        username = None
        callback_data = None
        
        if isinstance(message_or_callback, types.Message):
            user_id = message_or_callback.from_user.id
            username = message_or_callback.from_user.username or message_or_callback.from_user.first_name
            logger.info(f"🔍 [ADMIN_ONLY] Message від користувача: {username} (ID: {user_id}), функція: {func.__name__}")
        elif isinstance(message_or_callback, types.CallbackQuery):
            user_id = message_or_callback.from_user.id
            username = message_or_callback.from_user.username or message_or_callback.from_user.first_name
            callback_data = message_or_callback.data
            logger.info(f"🔍 [ADMIN_ONLY] CallbackQuery від користувача: {username} (ID: {user_id}), callback_data: {callback_data}, функція: {func.__name__}")
        
        # Детальне логування kwargs для перевірки чи передається state
        logger.info(f"🔍 [ADMIN_ONLY] kwargs keys: {list(kwargs.keys())}")
        if 'state' in kwargs:
            logger.info(f"✅ [ADMIN_ONLY] state присутній в kwargs")
        else:
            logger.warning(f"⚠️ [ADMIN_ONLY] state ВІДСУТНІЙ в kwargs!")
        
        logger.info(f"🔍 [ADMIN_ONLY] Перевірка доступу: user_id={user_id}, ADMIN_IDS={ADMIN_IDS}")
        
        if user_id not in ADMIN_IDS:
            logger.warning(f"❌ [ADMIN_ONLY] Спроба доступу до адмін функції від не-адміна: {username} (ID: {user_id}), ADMIN_IDS: {ADMIN_IDS}, функція: {func.__name__}")
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.answer("❌ У вас немає доступу до цієї команди.")
            elif isinstance(message_or_callback, types.CallbackQuery):
                await message_or_callback.answer("❌ У вас немає доступу до цієї функції.", show_alert=True)
            return
        
        logger.info(f"✅ [ADMIN_ONLY] Адмін доступ дозволено: {username} (ID: {user_id}), виконання функції: {func.__name__}")
        result = await func(message_or_callback, *args, **kwargs)
        logger.info(f"✅ [ADMIN_ONLY] Функція {func.__name__} завершена для користувача: {username} (ID: {user_id})")
        return result
    
    return wrapper
