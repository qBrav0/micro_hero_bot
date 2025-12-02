from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_admin_menu() -> ReplyKeyboardMarkup:
    """Адмін-панель"""
    keyboard = [
        [KeyboardButton(text="🎮 Управління іграми")],
        [KeyboardButton(text="📅 Управління розкладом")],
        [KeyboardButton(text="🎪 Управління подіями")],
        [KeyboardButton(text="🎅 Таємний Санта (адмін)")],
        [KeyboardButton(text="📊 Статистика")],
        [KeyboardButton(text="👥 Користувачі")],
        [KeyboardButton(text="📢 Сповіщення всім")],
        # [KeyboardButton(text="🎲 Заповнити тестовими іграми")],  # Приховано
        [KeyboardButton(text="ℹ️ Редагувати інформацію про клуб")],
        [KeyboardButton(text="🏠 Головне меню")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True,
        input_field_placeholder="Оберіть дію адміністратора..."
    )


def get_admin_games_menu() -> ReplyKeyboardMarkup:
    """Меню управління іграми"""
    keyboard = [
        [KeyboardButton(text="➕ Додати гру")],
        [KeyboardButton(text="📋 Список ігор")],
        [KeyboardButton(text="🔙 Назад до адмін-панелі")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def get_admin_schedule_menu() -> ReplyKeyboardMarkup:
    """Меню управління розкладом"""
    keyboard = [
        [KeyboardButton(text="➕ Додати гру в розклад")],
        [KeyboardButton(text="📋 Переглянути розклад")],
        [KeyboardButton(text="🔙 Назад до адмін-панелі")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


def get_admin_events_menu() -> ReplyKeyboardMarkup:
    """Меню управління подіями"""
    keyboard = [
        [KeyboardButton(text="➕ Створити подію")],
        [KeyboardButton(text="📋 Список подій")],
        [KeyboardButton(text="🔙 Назад до адмін-панелі")]
    ]
    
    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )
