from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu(is_admin: bool = False) -> ReplyKeyboardMarkup:
    """Головне меню для користувача"""
    keyboard = [
        [KeyboardButton(text="📅 Розклад ігор")],
        [KeyboardButton(text="🎮 Мої записи")],
        [KeyboardButton(text="🔔 Налаштування сповіщень")],
        [KeyboardButton(text="🏆 Топ-10 ігротеки")],
        [KeyboardButton(text="ℹ️ Про ігротеку"), KeyboardButton(text="💳 Оплата")]
    ]
    
    if is_admin:
        keyboard.append([KeyboardButton(text="⚙️ Адмін-панель")])
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію..."
    )


def get_back_to_menu() -> ReplyKeyboardMarkup:
    """Кнопка повернення до головного меню"""
    keyboard = [[KeyboardButton(text="🏠 Головне меню")]]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )
