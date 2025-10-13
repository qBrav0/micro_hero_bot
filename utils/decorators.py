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
        
        if isinstance(message_or_callback, types.Message):
            user_id = message_or_callback.from_user.id
            username = message_or_callback.from_user.username or message_or_callback.from_user.first_name
        elif isinstance(message_or_callback, types.CallbackQuery):
            user_id = message_or_callback.from_user.id
            username = message_or_callback.from_user.username or message_or_callback.from_user.first_name
        
        if user_id not in ADMIN_IDS:
            logger.warning(f"Спроба доступу до адмін функції від не-адміна: {username} (ID: {user_id}), ADMIN_IDS: {ADMIN_IDS}")
            if isinstance(message_or_callback, types.Message):
                await message_or_callback.answer("❌ У вас немає доступу до цієї команди.")
            elif isinstance(message_or_callback, types.CallbackQuery):
                await message_or_callback.answer("❌ У вас немає доступу до цієї функції.", show_alert=True)
            return
        
        logger.info(f"Адмін доступ дозволено: {username} (ID: {user_id})")
        return await func(message_or_callback, *args, **kwargs)
    
    return wrapper
