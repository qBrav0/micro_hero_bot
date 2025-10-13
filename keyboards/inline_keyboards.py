from datetime import date, timedelta
from typing import List, Optional
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_schedule_keyboard(sessions_by_date: dict, current_date: Optional[date] = None) -> InlineKeyboardMarkup:
    """Клавіатура для перегляду розкладу"""
    keyboard = []
    
    for session_date, sessions in sessions_by_date.items():
        date_str = session_date.strftime("%d.%m")
        keyboard.append([
            InlineKeyboardButton(
                text=f"📅 {date_str}",
                callback_data=f"schedule_date_{session_date.isoformat()}"
            )
        ])
    
    if not keyboard:
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Немає доступних ігор",
                callback_data="no_games"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_game_actions_keyboard(session_id: int, is_registered: bool, 
                              is_admin: bool = False) -> InlineKeyboardMarkup:
    """Клавіатура дій з грою"""
    keyboard = []
    
    if is_registered:
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Скасувати запис",
                callback_data=f"unregister_{session_id}"
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                text="✅ Записатися",
                callback_data=f"register_{session_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="👥 Список гравців",
            callback_data=f"players_list_{session_id}"
        )
    ])
    
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(
                text="🗑️ Видалити сесію",
                callback_data=f"admin_delete_session_{session_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад",
            callback_data="back_to_schedule"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_registration_keyboard(session_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для реєстрації на гру"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Записатися",
                callback_data=f"register_{session_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="back_to_schedule"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_games_list_keyboard(games: List, for_schedule: bool = False, page: int = 0, items_per_page: int = 7) -> InlineKeyboardMarkup:
    """Клавіатура зі списком ігор з пагінацією"""
    keyboard = []
    
    # Обчислюємо індекси для поточної сторінки
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    total_pages = (len(games) + items_per_page - 1) // items_per_page
    
    # Додаємо ігри для поточної сторінки
    page_games = games[start_idx:end_idx]
    
    for game in page_games:
        callback_prefix = "schedule_select_game" if for_schedule else "admin_game"
        keyboard.append([
            InlineKeyboardButton(
                text=f"🎮 {game.name}",
                callback_data=f"{callback_prefix}_{game.id}"
            )
        ])
    
    if not keyboard:
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Немає доступних ігор",
                callback_data="no_games"
            )
        ])
    
    # Додаємо кнопки пагінації
    if total_pages > 1:
        pagination_row = []
        
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton(
                    text="◀️ Попередня",
                    callback_data=f"games_page_{page-1}_{'schedule' if for_schedule else 'admin'}"
                )
            )
        
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="Наступна ▶️",
                    callback_data=f"games_page_{page+1}_{'schedule' if for_schedule else 'admin'}"
                )
            )
        
        if pagination_row:
            keyboard.append(pagination_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_date_selection_keyboard() -> InlineKeyboardMarkup:
    """Клавіатура для вибору дати (найближчі 7 днів)"""
    keyboard = []
    today = date.today()
    
    for i in range(7):
        current_date = today + timedelta(days=i)
        date_str = current_date.strftime("%d.%m")
        weekday_names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Нд"]
        weekday = weekday_names[current_date.weekday()]
        
        label = f"{weekday} {date_str}"
        if i == 0:
            label = f"Сьогодні ({date_str})"
        elif i == 1:
            label = f"Завтра ({date_str})"
        
        keyboard.append([
            InlineKeyboardButton(
                text=label,
                callback_data=f"select_date_{current_date.isoformat()}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_confirmation_keyboard(action: str, item_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для підтвердження дії"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Так",
                callback_data=f"confirm_{action}_{item_id}"
            ),
            InlineKeyboardButton(
                text="❌ Ні",
                callback_data="cancel_action"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_game_edit_keyboard(game_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для редагування гри"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="✏️ Редагувати назву",
                callback_data=f"edit_game_name_{game_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Редагувати опис",
                callback_data=f"edit_game_description_{game_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Змінити мін. кількість гравців",
                callback_data=f"edit_game_min_players_{game_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Змінити макс. кількість гравців",
                callback_data=f"edit_game_max_players_{game_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏱️ Змінити тривалість",
                callback_data=f"edit_game_duration_{game_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📸 Змінити зображення",
                callback_data=f"edit_game_image_{game_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Видалити гру",
                callback_data=f"delete_game_{game_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад до списку",
                callback_data="admin_games_list"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_my_registrations_keyboard(registrations: List) -> InlineKeyboardMarkup:
    """Клавіатура для моїх записів"""
    keyboard = []
    
    for reg in registrations:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🎮 Сесія #{reg.session_id}",
                callback_data=f"view_session_{reg.session_id}"
            )
        ])
    
    if not keyboard:
        keyboard.append([
            InlineKeyboardButton(
                text="❌ У вас немає активних записів",
                callback_data="no_registrations"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Головне меню",
            callback_data="back_to_menu"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)
