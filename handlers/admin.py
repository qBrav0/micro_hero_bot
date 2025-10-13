from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date, time
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_session
from services import GameService, ScheduleService
from keyboards import (
    get_admin_menu, get_admin_games_menu, get_admin_schedule_menu,
    get_games_list_keyboard, get_date_selection_keyboard, get_confirmation_keyboard
)
from utils.decorators import admin_only
from utils.validators import validate_time, validate_date, validate_players_count, validate_duration
from database.crud import get_game, get_registrations

router = Router()


# FSM стани для додавання гри
class AddGameStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_min_players = State()
    waiting_for_max_players = State()
    waiting_for_duration = State()
    waiting_for_image = State()


# FSM стани для створення розкладу
class CreateScheduleStates(StatesGroup):
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_game = State()


# FSM стани для редагування гри
class EditGameStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_min_players = State()
    waiting_for_max_players = State()
    waiting_for_duration = State()
    waiting_for_image = State()


@router.message(F.text == "⚙️ Адмін-панель")
@admin_only
async def show_admin_panel(message: Message):
    """Показати адмін-панель"""
    text = "⚙️ <b>Адмін-панель</b>\n\n"
    text += "Оберіть дію:"
    
    await message.answer(
        text,
        reply_markup=get_admin_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "🔙 Назад до адмін-панелі")
@admin_only
async def back_to_admin_panel(message: Message):
    """Повернутися до адмін-панелі"""
    await show_admin_panel(message)


# ===== УПРАВЛІННЯ ІГРАМИ =====

@router.message(F.text == "🎮 Управління іграми")
@admin_only
async def show_games_management(message: Message):
    """Показати меню управління іграми"""
    text = "🎮 <b>Управління іграми</b>\n\n"
    text += "Оберіть дію:"
    
    await message.answer(
        text,
        reply_markup=get_admin_games_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "➕ Додати гру")
@admin_only
async def start_add_game(message: Message, state: FSMContext):
    """Почати процес додавання гри"""
    await state.set_state(AddGameStates.waiting_for_name)
    await message.answer(
        "🎮 <b>Додавання нової гри</b>\n\n"
        "Введіть назву гри:",
        parse_mode="HTML"
    )


@router.message(AddGameStates.waiting_for_name)
async def process_game_name(message: Message, state: FSMContext):
    """Обробка назви гри"""
    await state.update_data(name=message.text)
    await state.set_state(AddGameStates.waiting_for_description)
    await message.answer("📝 Введіть опис гри:")


@router.message(AddGameStates.waiting_for_description)
async def process_game_description(message: Message, state: FSMContext):
    """Обробка опису гри"""
    await state.update_data(description=message.text)
    await state.set_state(AddGameStates.waiting_for_min_players)
    await message.answer("👥 Введіть мінімальну кількість гравців:")


@router.message(AddGameStates.waiting_for_min_players)
async def process_min_players(message: Message, state: FSMContext):
    """Обробка мінімальної кількості гравців"""
    try:
        min_players = int(message.text)
        if min_players < 1:
            await message.answer("⚠️ Мінімальна кількість гравців повинна бути більше 0")
            return
        
        await state.update_data(min_players=min_players)
        await state.set_state(AddGameStates.waiting_for_max_players)
        await message.answer("👥 Введіть максимальну кількість гравців:")
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.message(AddGameStates.waiting_for_max_players)
async def process_max_players(message: Message, state: FSMContext):
    """Обробка максимальної кількості гравців"""
    try:
        max_players = int(message.text)
        data = await state.get_data()
        min_players = data.get("min_players", 1)
        
        # Валідація
        valid, error_msg = validate_players_count(min_players, max_players)
        if not valid:
            await message.answer(error_msg)
            return
        
        await state.update_data(max_players=max_players)
        await state.set_state(AddGameStates.waiting_for_duration)
        await message.answer("⏱️ Введіть середню тривалість партії (в хвилинах):")
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.message(AddGameStates.waiting_for_duration)
async def process_duration(message: Message, state: FSMContext):
    """Обробка тривалості гри"""
    try:
        duration = int(message.text)
        
        # Валідація
        valid, error_msg = validate_duration(duration)
        if not valid:
            await message.answer(error_msg)
            return
        
        await state.update_data(avg_duration=duration)
        await state.set_state(AddGameStates.waiting_for_image)
        await message.answer(
            "📸 Надішліть зображення гри або введіть /skip щоб пропустити:"
        )
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.message(AddGameStates.waiting_for_image, F.photo)
async def process_game_image(message: Message, state: FSMContext):
    """Обробка зображення гри"""
    # Зберігаємо фото
    photo = message.photo[-1]  # Беремо найбільше фото
    
    # Створюємо шлях для збереження
    import os
    os.makedirs("static/images", exist_ok=True)
    
    file_path = f"static/images/{photo.file_id}.jpg"
    
    # Завантажуємо файл
    await message.bot.download(photo, destination=file_path)
    
    await state.update_data(image_path=file_path)
    await save_game(message, state)


@router.message(AddGameStates.waiting_for_image, F.text == "/skip")
async def skip_game_image(message: Message, state: FSMContext):
    """Пропустити зображення"""
    await state.update_data(image_path=None)
    await save_game(message, state)


async def save_game(message: Message, state: FSMContext):
    """Зберегти гру в базу даних"""
    data = await state.get_data()
    
    async for session in get_session():
        game = await GameService.create_new_game(
            session=session,
            name=data["name"],
            description=data["description"],
            min_players=data["min_players"],
            max_players=data["max_players"],
            avg_duration=data["avg_duration"],
            image_path=data.get("image_path")
        )
        
        await message.answer(
            f"✅ Гру <b>{game.name}</b> успішно додано!",
            reply_markup=get_admin_games_menu(),
            parse_mode="HTML"
        )
    
    await state.clear()


@router.message(F.text == "📋 Список ігор")
@admin_only
async def show_games_list(message: Message):
    """Показати список ігор"""
    async for session in get_session():
        games = await GameService.get_all_active_games(session)
        
        if not games:
            await message.answer("📋 Список ігор порожній")
            return
        
        text = "📋 <b>Список ігор:</b>\n\n"
        
        for i, game in enumerate(games, 1):
            text += f"{i}. 🎮 <b>{game.name}</b>\n"
            text += f"   👥 {game.min_players}-{game.max_players} гравців\n"
            text += f"   ⏱️ ~{game.avg_duration} хв\n\n"
        
        # Клавіатура для вибору гри
        keyboard = get_games_list_keyboard(games, for_schedule=False)
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin_games_list")
async def back_to_games_list(callback: CallbackQuery):
    """Повернутися до списку ігор"""
    await show_games_list_page(callback, page=0)


@router.callback_query(F.data.startswith("games_page_"))
async def handle_games_pagination(callback: CallbackQuery):
    """Обробка пагінації списку ігор"""
    parts = callback.data.split("_")
    page = int(parts[2])
    await show_games_list_page(callback, page=page)


async def show_games_list_page(callback: CallbackQuery, page: int = 0):
    """Показати сторінку списку ігор"""
    async for session in get_session():
        games = await GameService.get_all_active_games(session)
        
        if not games:
            await callback.message.edit_text("📋 Список ігор порожній")
            await callback.answer()
            return
        
        # Обчислюємо які ігри показувати
        items_per_page = 7
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        total_pages = (len(games) + items_per_page - 1) // items_per_page
        
        text = f"📋 <b>Список ігор</b> (Сторінка {page + 1}/{total_pages})\n\n"
        
        # Показуємо тільки ігри поточної сторінки
        page_games = games[start_idx:end_idx]
        for i, game in enumerate(page_games, start_idx + 1):
            text += f"{i}. 🎮 <b>{game.name}</b>\n"
            text += f"   👥 {game.min_players}-{game.max_players} гравців\n"
            text += f"   ⏱️ ~{game.avg_duration} хв\n\n"
        
        keyboard = get_games_list_keyboard(games, for_schedule=False, page=page)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("admin_game_"))
async def show_game_edit_menu(callback: CallbackQuery):
    """Показати меню редагування гри"""
    game_id = int(callback.data.split("_")[-1])
    
    async for session in get_session():
        game = await GameService.get_game_by_id(session, game_id)
        
        if not game:
            await callback.answer("❌ Гру не знайдено", show_alert=True)
            return
        
        text = GameService.format_game_info(game)
        text += "\n<b>Оберіть що хочете змінити:</b>"
        
        from keyboards import get_game_edit_keyboard
        keyboard = get_game_edit_keyboard(game_id)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


# ===== УПРАВЛІННЯ РОЗКЛАДОМ =====

@router.message(F.text == "📅 Управління розкладом")
@admin_only
async def show_schedule_management(message: Message):
    """Показати меню управління розкладом"""
    text = "📅 <b>Управління розкладом</b>\n\n"
    text += "Оберіть дію:"
    
    await message.answer(
        text,
        reply_markup=get_admin_schedule_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "➕ Додати гру в розклад")
@admin_only
async def start_create_schedule(message: Message, state: FSMContext):
    """Почати створення розкладу"""
    await state.set_state(CreateScheduleStates.waiting_for_date)
    
    text = "📅 <b>Додавання гри в розклад</b>\n\n"
    text += "Оберіть дату або введіть вручну (ДД.ММ.РРРР):"
    
    keyboard = get_date_selection_keyboard()
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("select_date_"))
async def process_date_selection(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору дати"""
    date_str = callback.data.split("_")[-1]
    selected_date = date.fromisoformat(date_str)
    
    await state.update_data(date=selected_date)
    await state.set_state(CreateScheduleStates.waiting_for_start_time)
    
    await callback.message.edit_text(
        f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n"
        "⏰ Введіть час початку (ЧЧ:ХХ):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(CreateScheduleStates.waiting_for_date)
async def process_custom_date(message: Message, state: FSMContext):
    """Обробка введеної дати"""
    valid, parsed_date, error_msg = validate_date(message.text)
    
    if not valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(date=parsed_date)
    await state.set_state(CreateScheduleStates.waiting_for_start_time)
    await message.answer("⏰ Введіть час початку (ЧЧ:ХХ):")


@router.message(CreateScheduleStates.waiting_for_start_time)
async def process_start_time(message: Message, state: FSMContext):
    """Обробка часу початку"""
    valid, parsed_time, error_msg = validate_time(message.text)
    
    if not valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(start_time=message.text)
    await state.set_state(CreateScheduleStates.waiting_for_end_time)
    await message.answer("⏰ Введіть час закінчення (ЧЧ:ХХ):")


@router.message(CreateScheduleStates.waiting_for_end_time)
async def process_end_time(message: Message, state: FSMContext):
    """Обробка часу закінчення"""
    valid, parsed_time, error_msg = validate_time(message.text)
    
    if not valid:
        await message.answer(error_msg)
        return
    
    data = await state.get_data()
    start_time_str = data.get("start_time", "00:00")
    
    # Перевіряємо, що час закінчення пізніше початку
    start_valid, start_time_obj, _ = validate_time(start_time_str)
    if start_time_obj >= parsed_time:
        await message.answer("⚠️ Час закінчення повинен бути пізніше часу початку")
        return
    
    await state.update_data(end_time=message.text)
    await state.set_state(CreateScheduleStates.waiting_for_game)
    
    # Показуємо список ігор
    async for session in get_session():
        games = await GameService.get_all_active_games(session)
        
        if not games:
            await message.answer(
                "❌ Немає доступних ігор. Спочатку додайте хоча б одну гру.",
                reply_markup=get_admin_schedule_menu()
            )
            await state.clear()
            return
        
        text = "🎮 Оберіть гру зі списку:"
        keyboard = get_games_list_keyboard(games, for_schedule=True)
        
        await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.startswith("schedule_select_game_"))
async def process_game_selection(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору гри для розкладу"""
    game_id = int(callback.data.split("_")[-1])
    
    data = await state.get_data()
    user_telegram_id = callback.from_user.id
    
    async for session in get_session():
        # Отримуємо user з бази даних
        from database import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, user_telegram_id)
        
        if not user:
            await callback.answer("❌ Помилка: користувача не знайдено", show_alert=True)
            await state.clear()
            return
        
        # Створюємо сесію з правильним user.id
        game_session = await ScheduleService.create_session(
            session=session,
            game_id=game_id,
            date=data["date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            created_by=user.id
        )
        
        game = await get_game(session, game_id)
        
        await callback.message.edit_text(
            f"✅ Гру <b>{game.name}</b> успішно додано в розклад!\n\n"
            f"📅 Дата: {data['date'].strftime('%d.%m.%Y')}\n"
            f"⏰ Час: {data['start_time']} - {data['end_time']}",
            parse_mode="HTML"
        )
    
    await state.clear()
    await callback.answer()


@router.message(F.text == "📋 Переглянути розклад")
@admin_only
async def view_admin_schedule(message: Message):
    """Переглянути розклад (адмін) з можливістю видалення"""
    async for db_session in get_session():
        sessions = await ScheduleService.get_upcoming_schedule(db_session, days=14)
        
        if not sessions:
            await message.answer("📅 На найближчі 14 днів немає запланованих ігор.")
            return
        
        text = "📅 <b>Розклад ігор (Адмін)</b>\n\n"
        text += "Оберіть сесію для управління:"
        
        # Створюємо клавіатуру з сесіями
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = []
        
        for game_session in sessions:
            game = await get_game(db_session, game_session.game_id)
            if not game:
                continue
            
            registrations = await get_registrations(db_session, game_session.id, active_only=True)
            players_count = len(registrations)
            
            from utils.helpers import format_date, format_time
            button_text = f"🎮 {game.name} | {format_date(game_session.date)} {format_time(game_session.start_time)} | {players_count}/{game.max_players}"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"admin_manage_session_{game_session.id}"
                )
            ])
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_manage_session_"))
async def admin_manage_session(callback: CallbackQuery):
    """Управління сесією (адмін)"""
    session_id = int(callback.data.split("_")[-1])
    
    async for db_session in get_session():
        from sqlmodel import select
        from database.models import GameSession
        
        result = await db_session.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session:
            await callback.answer("❌ Сесію не знайдено", show_alert=True)
            return
        
        game = await get_game(db_session, game_session.game_id)
        registrations = await get_registrations(db_session, session_id, active_only=True)
        
        from utils.helpers import format_date, format_time
        text = f"🎮 <b>{game.name}</b>\n\n"
        text += f"📅 <b>Дата:</b> {format_date(game_session.date)}\n"
        text += f"⏰ <b>Час:</b> {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n"
        text += f"👥 <b>Зареєстровано:</b> {len(registrations)}/{game.max_players}\n\n"
        text += "<b>Що ви хочете зробити?</b>"
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Список гравців",
                    callback_data=f"players_list_{session_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Видалити сесію",
                    callback_data=f"admin_delete_session_{session_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад до розкладу",
                    callback_data="admin_back_schedule"
                )
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "admin_back_schedule")
async def admin_back_schedule(callback: CallbackQuery):
    """Повернутися до розкладу"""
    async for db_session in get_session():
        sessions = await ScheduleService.get_upcoming_schedule(db_session, days=14)
        
        if not sessions:
            await callback.message.edit_text("📅 На найближчі 14 днів немає запланованих ігор.")
            await callback.answer()
            return
        
        text = "📅 <b>Розклад ігор (Адмін)</b>\n\n"
        text += "Оберіть сесію для управління:"
        
        # Створюємо клавіатуру з сесіями
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = []
        
        for game_session in sessions:
            game = await get_game(db_session, game_session.game_id)
            if not game:
                continue
            
            registrations = await get_registrations(db_session, game_session.id, active_only=True)
            players_count = len(registrations)
            
            from utils.helpers import format_date, format_time
            button_text = f"🎮 {game.name} | {format_date(game_session.date)} {format_time(game_session.start_time)} | {players_count}/{game.max_players}"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"admin_manage_session_{game_session.id}"
                )
            ])
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()


# ===== СТАТИСТИКА =====

@router.message(F.text == "📊 Статистика")
@admin_only
async def show_statistics(message: Message):
    """Показати статистику"""
    async for session in get_session():
        from sqlmodel import select, func
        from database.models import Registration, Game, GameSession
        
        # Загальна кількість реєстрацій
        result = await session.execute(
            select(func.count(Registration.id)).where(Registration.is_active == True)
        )
        total_registrations = result.scalar()
        
        # Кількість ігор
        result = await session.execute(
            select(func.count(Game.id)).where(Game.is_active == True)
        )
        total_games = result.scalar()
        
        # Кількість майбутніх сесій
        from datetime import date
        result = await session.execute(
            select(func.count(GameSession.id)).where(GameSession.date >= date.today())
        )
        upcoming_sessions = result.scalar()
        
        text = "📊 <b>Статистика</b>\n\n"
        text += f"🎮 <b>Ігор в базі:</b> {total_games}\n"
        text += f"📅 <b>Майбутніх сесій:</b> {upcoming_sessions}\n"
        text += f"👥 <b>Активних реєстрацій:</b> {total_registrations}\n"
        
        await message.answer(text, parse_mode="HTML")


# ===== КОРИСТУВАЧІ =====

@router.message(F.text == "👥 Користувачі")
@admin_only
async def show_users(message: Message):
    """Показати користувачів"""
    async for session in get_session():
        from sqlmodel import select, func
        from database.models import User
        
        # Загальна кількість користувачів
        result = await session.execute(
            select(func.count(User.id))
        )
        total_users = result.scalar()
        
        # Отримуємо останніх 10 користувачів
        result = await session.execute(
            select(User).order_by(User.created_at.desc()).limit(10)
        )
        recent_users = result.scalars().all()
        
        text = "👥 <b>Користувачі</b>\n\n"
        text += f"<b>Всього користувачів:</b> {total_users}\n\n"
        text += "<b>Останні 10 зареєстрованих користувачів:</b>\n"
        
        from database import get_user_attended_sessions_count
        
        for user in recent_users:
            username_str = f"@{user.username}" if user.username else "без username"
            admin_badge = " 👑" if user.is_admin else ""
            
            # Отримуємо кількість відвіданих сесій
            attended_count = await get_user_attended_sessions_count(session, user.id)
            
            text += f"• {user.first_name} ({username_str}){admin_badge}"
            if attended_count > 0:
                text += f" - відвідав {attended_count} сесій"
            text += "\n"
        
        await message.answer(text, parse_mode="HTML")


# ===== РЕДАГУВАННЯ ІГОР =====

@router.callback_query(F.data.startswith("edit_game_name_"))
async def start_edit_game_name(callback: CallbackQuery, state: FSMContext):
    """Почати редагування назви гри"""
    game_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_game_id=game_id)
    await state.set_state(EditGameStates.waiting_for_name)
    
    await callback.message.edit_text("✏️ Введіть нову назву гри:")
    await callback.answer()


@router.message(EditGameStates.waiting_for_name)
async def process_edit_game_name(message: Message, state: FSMContext):
    """Обробка нової назви гри"""
    data = await state.get_data()
    game_id = data.get("edit_game_id")
    
    async for session in get_session():
        game = await GameService.get_game_by_id(session, game_id)
        if game:
            await GameService.update_game_info(session, game, name=message.text)
            await message.answer(
                f"✅ Назву гри змінено на: <b>{message.text}</b>",
                reply_markup=get_admin_games_menu(),
                parse_mode="HTML"
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_game_description_"))
async def start_edit_game_description(callback: CallbackQuery, state: FSMContext):
    """Почати редагування опису гри"""
    game_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_game_id=game_id)
    await state.set_state(EditGameStates.waiting_for_description)
    
    await callback.message.edit_text("📝 Введіть новий опис гри:")
    await callback.answer()


@router.message(EditGameStates.waiting_for_description)
async def process_edit_game_description(message: Message, state: FSMContext):
    """Обробка нового опису гри"""
    data = await state.get_data()
    game_id = data.get("edit_game_id")
    
    async for session in get_session():
        game = await GameService.get_game_by_id(session, game_id)
        if game:
            await GameService.update_game_info(session, game, description=message.text)
            await message.answer(
                "✅ Опис гри змінено!",
                reply_markup=get_admin_games_menu()
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("edit_game_min_players_"))
async def start_edit_min_players(callback: CallbackQuery, state: FSMContext):
    """Почати редагування мінімальної кількості гравців"""
    game_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_game_id=game_id)
    await state.set_state(EditGameStates.waiting_for_min_players)
    
    await callback.message.edit_text("👥 Введіть нову мінімальну кількість гравців:")
    await callback.answer()


@router.message(EditGameStates.waiting_for_min_players)
async def process_edit_min_players(message: Message, state: FSMContext):
    """Обробка нової мінімальної кількості гравців"""
    try:
        min_players = int(message.text)
        if min_players < 1:
            await message.answer("⚠️ Мінімальна кількість гравців повинна бути більше 0")
            return
        
        data = await state.get_data()
        game_id = data.get("edit_game_id")
        
        async for session in get_session():
            game = await GameService.get_game_by_id(session, game_id)
            if game:
                # Перевіряємо що мінімум не більший за максимум
                if min_players > game.max_players:
                    await message.answer(
                        f"⚠️ Мінімальна кількість не може перевищувати максимальну ({game.max_players})"
                    )
                    return
                
                await GameService.update_game_info(session, game, min_players=min_players)
                await message.answer(
                    f"✅ Мінімальна кількість гравців змінена на: {min_players}",
                    reply_markup=get_admin_games_menu()
                )
        
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.callback_query(F.data.startswith("edit_game_max_players_"))
async def start_edit_max_players(callback: CallbackQuery, state: FSMContext):
    """Почати редагування максимальної кількості гравців"""
    game_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_game_id=game_id)
    await state.set_state(EditGameStates.waiting_for_max_players)
    
    await callback.message.edit_text("👥 Введіть нову максимальну кількість гравців:")
    await callback.answer()


@router.message(EditGameStates.waiting_for_max_players)
async def process_edit_max_players(message: Message, state: FSMContext):
    """Обробка нової максимальної кількості гравців"""
    try:
        max_players = int(message.text)
        
        data = await state.get_data()
        game_id = data.get("edit_game_id")
        
        async for session in get_session():
            game = await GameService.get_game_by_id(session, game_id)
            if game:
                # Валідація
                valid, error_msg = validate_players_count(game.min_players, max_players)
                if not valid:
                    await message.answer(error_msg)
                    return
                
                await GameService.update_game_info(session, game, max_players=max_players)
                await message.answer(
                    f"✅ Максимальна кількість гравців змінена на: {max_players}",
                    reply_markup=get_admin_games_menu()
                )
        
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.callback_query(F.data.startswith("edit_game_duration_"))
async def start_edit_duration(callback: CallbackQuery, state: FSMContext):
    """Почати редагування тривалості гри"""
    game_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_game_id=game_id)
    await state.set_state(EditGameStates.waiting_for_duration)
    
    await callback.message.edit_text("⏱️ Введіть нову середню тривалість партії (в хвилинах):")
    await callback.answer()


@router.message(EditGameStates.waiting_for_duration)
async def process_edit_duration(message: Message, state: FSMContext):
    """Обробка нової тривалості гри"""
    try:
        duration = int(message.text)
        
        # Валідація
        valid, error_msg = validate_duration(duration)
        if not valid:
            await message.answer(error_msg)
            return
        
        data = await state.get_data()
        game_id = data.get("edit_game_id")
        
        async for session in get_session():
            game = await GameService.get_game_by_id(session, game_id)
            if game:
                await GameService.update_game_info(session, game, avg_duration=duration)
                await message.answer(
                    f"✅ Тривалість гри змінена на: {duration} хв",
                    reply_markup=get_admin_games_menu()
                )
        
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.callback_query(F.data.startswith("edit_game_image_"))
async def start_edit_image(callback: CallbackQuery, state: FSMContext):
    """Почати редагування зображення гри"""
    game_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_game_id=game_id)
    await state.set_state(EditGameStates.waiting_for_image)
    
    await callback.message.edit_text("📸 Надішліть нове зображення гри:")
    await callback.answer()


@router.message(EditGameStates.waiting_for_image, F.photo)
async def process_edit_image(message: Message, state: FSMContext):
    """Обробка нового зображення гри"""
    photo = message.photo[-1]
    
    import os
    os.makedirs("static/images", exist_ok=True)
    file_path = f"static/images/{photo.file_id}.jpg"
    await message.bot.download(photo, destination=file_path)
    
    data = await state.get_data()
    game_id = data.get("edit_game_id")
    
    async for session in get_session():
        game = await GameService.get_game_by_id(session, game_id)
        if game:
            await GameService.update_game_info(session, game, image_path=file_path)
            await message.answer(
                "✅ Зображення гри змінено!",
                reply_markup=get_admin_games_menu()
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("delete_game_"))
async def confirm_delete_game(callback: CallbackQuery):
    """Підтвердження видалення гри"""
    game_id = int(callback.data.split("_")[-1])
    
    async for session in get_session():
        game = await GameService.get_game_by_id(session, game_id)
        if not game:
            await callback.answer("❌ Гру не знайдено", show_alert=True)
            return
        
        from keyboards import get_confirmation_keyboard
        text = f"⚠️ Ви впевнені що хочете видалити гру <b>{game.name}</b>?\n\n"
        text += "Це також видалить всі сесії та реєстрації на цю гру."
        
        keyboard = get_confirmation_keyboard("delete_game", game_id)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_game_"))
async def delete_game_confirmed(callback: CallbackQuery):
    """Видалити гру після підтвердження"""
    game_id = int(callback.data.split("_")[-1])
    
    async for session in get_session():
        success = await GameService.deactivate_game(session, game_id)
        if success:
            await callback.message.edit_text("✅ Гру успішно видалено!")
            await callback.answer()
        else:
            await callback.answer("❌ Помилка при видаленні гри", show_alert=True)


@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery):
    """Скасувати дію"""
    await callback.message.edit_text("❌ Дію скасовано")
    await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_session_"))
async def admin_delete_session(callback: CallbackQuery):
    """Видалити сесію гри (тільки для адмінів)"""
    session_id = int(callback.data.split("_")[-1])
    
    async for db_session in get_session():
        from sqlmodel import select
        from database.models import GameSession
        from database.crud import get_game
        
        # Отримуємо сесію
        result = await db_session.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session:
            await callback.answer("❌ Сесію не знайдено", show_alert=True)
            return
        
        # Отримуємо гру для показу назви
        game = await get_game(db_session, game_session.game_id)
        game_name = game.name if game else "Невідома гра"
        
        # Показуємо підтвердження
        from keyboards import get_confirmation_keyboard
        text = f"⚠️ <b>Видалення сесії гри</b>\n\n"
        text += f"🎮 Гра: <b>{game_name}</b>\n"
        text += f"📅 Дата: {game_session.date.strftime('%d.%m.%Y')}\n"
        text += f"⏰ Час: {game_session.start_time.strftime('%H:%M')}\n\n"
        text += "Ви впевнені що хочете видалити цю сесію?\n"
        text += "Всі реєстрації на цю гру будуть скасовані."
        
        keyboard = get_confirmation_keyboard("delete_session", session_id)
        
        # Перевіряємо чи є фото
        has_photo = callback.message.photo is not None and len(callback.message.photo) > 0
        
        if has_photo:
            await callback.message.edit_caption(
                caption=text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        else:
            await callback.message.edit_text(
                text,
                reply_markup=keyboard,
                parse_mode="HTML"
            )
        
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_session_"))
async def confirm_delete_session(callback: CallbackQuery):
    """Підтвердження видалення сесії"""
    session_id = int(callback.data.split("_")[-1])
    
    async for db_session in get_session():
        success = await ScheduleService.delete_session(db_session, session_id)
        
        if success:
            text = "✅ Сесію успішно видалено!"
            
            # Перевіряємо чи є фото
            has_photo = callback.message.photo is not None and len(callback.message.photo) > 0
            
            if has_photo:
                await callback.message.delete()
                await callback.message.answer(text)
            else:
                await callback.message.edit_text(text)
            
            await callback.answer()
        else:
            await callback.answer("❌ Помилка при видаленні сесії", show_alert=True)
