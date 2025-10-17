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


def get_schedule_paginated_keyboard(sessions_by_date: dict, page: int = 0, items_per_page: int = 7) -> InlineKeyboardMarkup:
    """Клавіатура для перегляду розкладу з пагінацією"""
    from utils.helpers import format_date
    
    keyboard = []
    
    # Конвертуємо словник в список для пагінації
    dates_list = list(sessions_by_date.items())
    total_pages = (len(dates_list) + items_per_page - 1) // items_per_page
    
    # Обчислюємо індекси для поточної сторінки
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    page_dates = dates_list[start_idx:end_idx]
    
    # Додаємо дати для поточної сторінки
    for session_date, sessions in page_dates:
        # Використовуємо format_date для отримання дня тижня
        formatted_date = format_date(session_date)
        # Скорочуємо для кнопки (залишаємо тільки день тижня і дату)
        short_date = formatted_date.split(',')[0] + ', ' + session_date.strftime('%d.%m')
        
        # Підраховуємо кількість ігор та подій
        games_count = 0
        events_count = 0
        
        for item in sessions:
            if hasattr(item, 'game_id'):  # Це ігрова сесія
                games_count += 1
            elif hasattr(item, 'title'):  # Це подія
                events_count += 1
        
        # Формуємо текст кнопки
        items_text = []
        if games_count > 0:
            items_text.append(f"{games_count} ігор")
        if events_count > 0:
            items_text.append(f"{events_count} подій")
        
        if items_text:
            items_str = " + ".join(items_text)
            button_text = f"📅 {short_date} ({items_str})"
        else:
            button_text = f"📅 {short_date}"
        
        keyboard.append([
            InlineKeyboardButton(
                text=button_text,
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
    
    # Додаємо кнопки пагінації
    if total_pages > 1:
        pagination_row = []
        
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton(
                    text="◀️ Попередня",
                    callback_data=f"schedule_page_{page-1}"
                )
            )
        
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="Наступна ▶️",
                    callback_data=f"schedule_page_{page+1}"
                )
            )
        
        if pagination_row:
            keyboard.append(pagination_row)
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_game_actions_keyboard(session_id: int, is_registered: bool, 
                              is_admin: bool = False, context: str = "schedule", 
                              date_str: str = None) -> InlineKeyboardMarkup:
    """Клавіатура дій з грою
    
    Args:
        session_id: ID сесії
        is_registered: Чи зареєстрований користувач
        is_admin: Чи є користувач адміном
        context: Контекст відкриття ('schedule', 'my_registrations', 'date')
        date_str: Дата у форматі ISO (для повернення в меню дня)
    """
    keyboard = []
    
    # Формуємо callback_data залежно від контексту
    if context == "date" and date_str:
        register_callback = f"register_{session_id}_date_{date_str}"
        unregister_callback = f"unregister_{session_id}_date_{date_str}"
        players_callback = f"players_list_{session_id}_date_{date_str}"
    elif context == "my_registrations":
        register_callback = f"register_{session_id}_my_registrations"
        unregister_callback = f"unregister_{session_id}_my_registrations"
        players_callback = f"players_list_{session_id}_my_registrations"
    else:
        register_callback = f"register_{session_id}"
        unregister_callback = f"unregister_{session_id}"
        players_callback = f"players_list_{session_id}"
    
    if is_registered:
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Скасувати запис",
                callback_data=unregister_callback
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                text="✅ Записатися",
                callback_data=register_callback
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="👥 Список гравців",
            callback_data=players_callback
        )
    ])
    
    if is_admin:
        keyboard.append([
            InlineKeyboardButton(
                text="🗑️ Видалити сесію",
                callback_data=f"admin_delete_session_{session_id}"
            )
        ])
    
    # Кнопка "Назад" залежить від контексту
    if context == "my_registrations":
        back_text = "🔙 До моїх записів"
        back_callback = "back_to_my_registrations"
    elif context == "date" and date_str:
        back_text = "🔙 До ігор дня"
        back_callback = f"schedule_date_{date_str}"
    else:
        back_text = "🔙 До розкладу"
        back_callback = "back_to_schedule"
    
    keyboard.append([
        InlineKeyboardButton(
            text=back_text,
            callback_data=back_callback
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


# ===== EVENT KEYBOARDS =====

def get_events_list_keyboard(events: List, for_registration: bool = False, page: int = 0) -> InlineKeyboardMarkup:
    """Клавіатура для списку подій"""
    keyboard = []
    
    # Обчислюємо які події показувати
    items_per_page = 7
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    total_pages = (len(events) + items_per_page - 1) // items_per_page
    
    # Показуємо тільки події поточної сторінки
    page_events = events[start_idx:end_idx]
    
    for event in page_events:
        if for_registration:
            callback_data = f"event_register_{event.id}"
            text = f"🎪 {event.title}"
        else:
            callback_data = f"admin_event_{event.id}"
            text = f"🎪 {event.title}"
        
        keyboard.append([
            InlineKeyboardButton(
                text=text,
                callback_data=callback_data
            )
        ])
    
    # Додаємо навігацію
    nav_buttons = []
    if page > 0:
        nav_buttons.append(
            InlineKeyboardButton(
                text="◀️ Попередня",
                callback_data=f"events_page_{page-1}_{'register' if for_registration else 'admin'}"
            )
        )
    
    if page < total_pages - 1:
        nav_buttons.append(
            InlineKeyboardButton(
                text="Наступна ▶️",
                callback_data=f"events_page_{page+1}_{'register' if for_registration else 'admin'}"
            )
        )
    
    if nav_buttons:
        keyboard.append(nav_buttons)
    
    # Додаємо кнопку назад
    if for_registration:
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Головне меню",
                callback_data="back_to_menu"
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                text="🔙 Назад",
                callback_data="admin_events_list"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_event_actions_keyboard(event_id: int, is_registered: bool = False) -> InlineKeyboardMarkup:
    """Клавіатура дій для події"""
    keyboard = []
    
    if is_registered:
        keyboard.append([
            InlineKeyboardButton(
                text="❌ Скасувати реєстрацію",
                callback_data=f"event_cancel_{event_id}"
            )
        ])
    else:
        keyboard.append([
            InlineKeyboardButton(
                text="✅ Зареєструватися",
                callback_data=f"event_register_{event_id}"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="👥 Список учасників",
            callback_data=f"event_participants_list_{event_id}"
        )
    ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Назад до дат",
            callback_data="back_to_events"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_event_edit_keyboard(event_id: int) -> InlineKeyboardMarkup:
    """Клавіатура для редагування події"""
    keyboard = [
        [
            InlineKeyboardButton(
                text="🏷️ Редагувати назву",
                callback_data=f"start_edit_event_title_{event_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📝 Редагувати опис",
                callback_data=f"start_edit_event_description_{event_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📅 Змінити дату",
                callback_data=f"start_edit_event_date_{event_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="⏰ Змінити час",
                callback_data=f"start_edit_event_time_{event_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Змінити кількість учасників",
                callback_data=f"start_edit_event_participants_{event_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="💳 Змінити тип оплати",
                callback_data=f"start_edit_event_payment_{event_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="📸 Змінити зображення",
                callback_data=f"start_edit_event_image_{event_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="👥 Список учасників",
                callback_data=f"admin_participants_list_{event_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🗑️ Видалити подію",
                callback_data=f"delete_event_{event_id}"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 Назад до списку",
                callback_data="admin_events_list"
            )
        ]
    ]
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def get_my_event_registrations_keyboard(registrations: List) -> InlineKeyboardMarkup:
    """Клавіатура для моїх реєстрацій на події"""
    keyboard = []
    
    for reg in registrations:
        keyboard.append([
            InlineKeyboardButton(
                text=f"🎪 Подія #{reg.event_id}",
                callback_data=f"view_event_{reg.event_id}"
            )
        ])
    
    if not keyboard:
        keyboard.append([
            InlineKeyboardButton(
                text="❌ У вас немає активних реєстрацій на події",
                callback_data="no_event_registrations"
            )
        ])
    
    keyboard.append([
        InlineKeyboardButton(
            text="🔙 Головне меню",
            callback_data="back_to_menu"
        )
    ])
    
    return InlineKeyboardMarkup(inline_keyboard=keyboard)