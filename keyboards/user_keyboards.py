from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_menu(is_admin: bool = False, is_secret_santa_participant: bool = False) -> ReplyKeyboardMarkup:
    """Головне меню для користувача"""
    keyboard = [
        [KeyboardButton(text="📅 Розклад ігротеки")],
        [KeyboardButton(text="🎮 Мої записи")],
        [KeyboardButton(text="🎲 База ігор")],
        [KeyboardButton(text="🔔 Налаштування сповіщень")],
        [KeyboardButton(text="🏆 Топ-10 ігротеки")],
    ]
    
    # Кнопка Таємний Санта показується тільки для зареєстрованих учасників
    if is_secret_santa_participant:
        keyboard.append([KeyboardButton(text="🎅 Таємний Санта")])
    
    keyboard.append([KeyboardButton(text="ℹ️ Про ігротеку"), KeyboardButton(text="💳 Оплата")])
    
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
