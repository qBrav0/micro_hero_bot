from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
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
from utils.validators import validate_time, validate_date, validate_players_count, validate_duration, normalize_time
from utils.helpers import format_date, format_time
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
    waiting_for_adult_price = State()
    waiting_for_child_price = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_payment_type = State()
    waiting_for_game = State()


# FSM стани для редагування гри
class EditGameStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_min_players = State()
    waiting_for_max_players = State()
    waiting_for_duration = State()
    waiting_for_image = State()


# FSM стани для редагування інформації про клуб
class EditClubInfoStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_description = State()
    waiting_for_about_text = State()
    waiting_for_payment_info = State()
    waiting_for_card_number = State()
    waiting_for_bank_link = State()


# FSM стани для кіку гравця
class KickPlayerStates(StatesGroup):
    waiting_for_reason = State()
    waiting_for_confirmation = State()


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
async def back_to_admin_panel(message: Message, state: FSMContext):
    """Повернутися до адмін-панелі"""
    await state.clear()  # Очищаємо FSM стан
    await show_admin_panel(message)


@router.callback_query(F.data == "admin_back")
@admin_only
async def admin_back_callback(callback: CallbackQuery, state: FSMContext):
    """Повернутися до адмін-панелі з callback"""
    await state.clear()  # Очищаємо FSM стан
    await show_admin_panel(callback.message)
    await callback.answer()


# ===== УПРАВЛІННЯ ІГРАМИ =====

@router.message(F.text == "🎮 Управління іграми")
@admin_only
async def show_games_management(message: Message, state: FSMContext):
    """Показати меню управління іграми"""
    # Перевіряємо чи не в процесі створення щось
    current_state = await state.get_state()
    if current_state is None:
        # Тільки очищаємо якщо не в FSM процесі
        await state.clear()
    
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
async def handle_games_pagination(callback: CallbackQuery, state: FSMContext):
    """Обробка пагінації списку ігор"""
    parts = callback.data.split("_")
    page = int(parts[2])
    page_type = parts[3] if len(parts) > 3 else "admin"  # schedule або admin
    
    if page_type == "schedule":
        await show_schedule_games_list_page(callback, state, page=page)
    else:
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


async def show_schedule_games_list_page(callback: CallbackQuery, state: FSMContext, page: int = 0):
    """Показати сторінку списку ігор для вибору в розклад"""
    async for session in get_session():
        games = await GameService.get_all_active_games(session)
        
        if not games:
            await callback.message.edit_text("❌ Немає доступних ігор")
            await callback.answer()
            return
        
        # Обчислюємо які ігри показувати
        items_per_page = 7
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        total_pages = (len(games) + items_per_page - 1) // items_per_page
        
        text = f"🎮 <b>Оберіть гру зі списку</b> (Сторінка {page + 1}/{total_pages}):"
        
        keyboard = get_games_list_keyboard(games, for_schedule=True, page=page)
        
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
async def show_schedule_management(message: Message, state: FSMContext):
    """Показати меню управління розкладом"""
    # Перевіряємо чи не в процесі створення щось
    current_state = await state.get_state()
    if current_state is None:
        # Тільки очищаємо якщо не в FSM процесі
        await state.clear()
    
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
@admin_only
async def process_date_selection(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору дати"""
    date_str = callback.data.split("_")[-1]
    selected_date = date.fromisoformat(date_str)
    
    await state.update_data(date=selected_date)
    
    # Перевіряємо чи є реально активні сесії на цей день
    from database import get_session, get_day_pricing
    from sqlmodel import select
    from database.models import GameSession
    
    async for db_session in get_session():
        # Перевіряємо чи є сесії на цю дату
        result = await db_session.execute(
            select(GameSession).where(GameSession.date == selected_date)
        )
        existing_sessions = result.scalars().all()
        
        if existing_sessions:
            # Є сесії на цей день - використовуємо існуючу ціну
            pricing = await get_day_pricing(db_session, selected_date)
            
            if pricing:
                await state.update_data(
                    adult_price=pricing.adult_price,
                    child_price=pricing.child_price,
                    pricing_exists=True
                )
                await state.set_state(CreateScheduleStates.waiting_for_start_time)
                await callback.message.edit_text(
                    f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n"
                    f"💰 Ціни на цей день вже встановлені:\n"
                    f"• Дорослі: {pricing.adult_price} грн\n"
                    f"• Діти до 18: {pricing.child_price} грн\n\n"
                    f"⏰ Введіть час початку (ЧЧ:ХХ):",
                    parse_mode="HTML"
                )
            else:
                # Є сесії але немає ціни (не повинно статися, але на всяк)
                await state.update_data(pricing_exists=False)
                await state.set_state(CreateScheduleStates.waiting_for_adult_price)
                await callback.message.edit_text(
                    f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n"
                    f"💰 Введіть ціну входу для дорослих (в грн):",
                    parse_mode="HTML"
                )
        else:
            # Немає сесій на цей день - це перша сесія, запитуємо ціну
            await state.update_data(pricing_exists=False)
            await state.set_state(CreateScheduleStates.waiting_for_adult_price)
            await callback.message.edit_text(
                f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n"
                f"💰 Це перша сесія на цей день.\n\n"
                f"Введіть ціну входу для дорослих (в грн):",
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
    
    # Перевіряємо чи є реально активні сесії на цей день
    from database import get_session, get_day_pricing
    from sqlmodel import select
    from database.models import GameSession
    
    async for db_session in get_session():
        # Перевіряємо чи є сесії на цю дату
        result = await db_session.execute(
            select(GameSession).where(GameSession.date == parsed_date)
        )
        existing_sessions = result.scalars().all()
        
        if existing_sessions:
            # Є сесії на цей день - використовуємо існуючу ціну
            pricing = await get_day_pricing(db_session, parsed_date)
            
            if pricing:
                await state.update_data(
                    adult_price=pricing.adult_price,
                    child_price=pricing.child_price,
                    pricing_exists=True
                )
                await state.set_state(CreateScheduleStates.waiting_for_start_time)
                await message.answer(
                    f"💰 Ціни на {parsed_date.strftime('%d.%m.%Y')} вже встановлені:\n"
                    f"• Дорослі: {pricing.adult_price} грн\n"
                    f"• Діти до 18: {pricing.child_price} грн\n\n"
                    f"⏰ Введіть час початку (ЧЧ:ХХ):"
                )
            else:
                # Є сесії але немає ціни (не повинно статися, але на всяк)
                await state.update_data(pricing_exists=False)
                await state.set_state(CreateScheduleStates.waiting_for_adult_price)
                await message.answer(
                    f"💰 Введіть ціну входу для дорослих (в грн):"
                )
        else:
            # Немає сесій на цей день - це перша сесія, запитуємо ціну
            await state.update_data(pricing_exists=False)
            await state.set_state(CreateScheduleStates.waiting_for_adult_price)
            await message.answer(
                f"💰 Це перша сесія на {parsed_date.strftime('%d.%m.%Y')}.\n\n"
                f"Введіть ціну входу для дорослих (в грн):"
            )


@router.message(CreateScheduleStates.waiting_for_adult_price)
@admin_only
async def process_adult_price(message: Message, state: FSMContext):
    """Обробка ціни для дорослих"""
    try:
        price = int(message.text.strip())
        if price < 0:
            await message.answer("❌ Ціна не може бути негативною. Спробуйте ще раз:")
            return
        
        await state.update_data(adult_price=price)
        await state.set_state(CreateScheduleStates.waiting_for_child_price)
        await message.answer("💰 Введіть ціну входу для дітей до 18 років (в грн):")
    except ValueError:
        await message.answer("❌ Введіть коректне число. Спробуйте ще раз:")


@router.message(CreateScheduleStates.waiting_for_child_price)
@admin_only
async def process_child_price(message: Message, state: FSMContext):
    """Обробка ціни для дітей"""
    try:
        price = int(message.text.strip())
        if price < 0:
            await message.answer("❌ Ціна не може бути негативною. Спробуйте ще раз:")
            return
        
        await state.update_data(child_price=price)
        await state.set_state(CreateScheduleStates.waiting_for_start_time)
        await message.answer("⏰ Введіть час початку (ЧЧ:ХХ):")
    except ValueError:
        await message.answer("❌ Введіть коректне число. Спробуйте ще раз:")


@router.message(CreateScheduleStates.waiting_for_start_time)
async def process_start_time(message: Message, state: FSMContext):
    """Обробка часу початку"""
    valid, parsed_time, error_msg = validate_time(message.text)
    
    if not valid:
        await message.answer(error_msg)
        return
    
    normalized_time = normalize_time(message.text)
    await state.update_data(start_time=normalized_time)
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
    
    normalized_time = normalize_time(message.text)
    await state.update_data(end_time=normalized_time)
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
    keyboard = get_games_list_keyboard(games, for_schedule=True, page=0)
    
    await message.answer(text, reply_markup=keyboard)


@router.callback_query(F.data.in_(["payment_included", "payment_free", "payment_donate"]))
@admin_only
async def process_payment_type(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору типу оплати та створення сесії"""
    payment_types = {
        "payment_included": "included",
        "payment_free": "free",
        "payment_donate": "donate"
    }
    
    payment_type = payment_types[callback.data]
    data = await state.get_data()
    user_telegram_id = callback.from_user.id
    
    async for session in get_session():
        from database import get_user_by_telegram_id, create_day_pricing, get_day_pricing, update_day_pricing
        user = await get_user_by_telegram_id(session, user_telegram_id)
        
        if not user:
            await callback.answer("❌ Помилка: користувача не знайдено", show_alert=True)
            await state.clear()
            return
        
        # Створюємо або оновлюємо ціноутворення для дня, якщо є дані про ціни
        if "adult_price" in data and "child_price" in data:
            existing_pricing = await get_day_pricing(session, data["date"])
            if existing_pricing:
                # Оновлюємо існуючий запис новими цінами
                await update_day_pricing(
                    session=session,
                    pricing_id=existing_pricing.id,
                    adult_price=data["adult_price"],
                    child_price=data["child_price"]
                )
            else:
                # Створюємо новий запис тільки якщо його ще немає
                await create_day_pricing(
                    session=session,
                    date=data["date"],
                    adult_price=data["adult_price"],
                    child_price=data["child_price"]
                )
        
        # Створюємо сесію з обраним типом оплати
        game_session = await ScheduleService.create_session(
            session=session,
            game_id=data["game_id"],
            date=data["date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            payment_type=payment_type,
            created_by=user.id
        )
        
        game = await get_game(session, data["game_id"])
        
        payment_type_text = {
            "included": "✅ Входить в оплату за вхід",
            "free": "🎁 Безкоштовна",
            "donate": "💝 Free donate"
        }
        
        await callback.message.edit_text(
            f"✅ Гру <b>{game.name}</b> успішно додано в розклад!\n\n"
            f"📅 Дата: {data['date'].strftime('%d.%m.%Y')}\n"
            f"⏰ Час: {data['start_time']} - {data['end_time']}\n"
            f"💳 Оплата: {payment_type_text.get(payment_type, 'Входить в оплату')}",
            parse_mode="HTML"
        )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("schedule_select_game_"))
@admin_only
async def process_game_selection(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору гри для розкладу"""
    game_id = int(callback.data.split("_")[-1])
    
    data = await state.get_data()
    await state.update_data(game_id=game_id)
    
    # Завжди запитуємо тип оплати
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Входить в оплату за вхід", callback_data="payment_included")],
        [InlineKeyboardButton(text="🎁 Безкоштовна", callback_data="payment_free")],
        [InlineKeyboardButton(text="💝 Free donate", callback_data="payment_donate")]
    ])
    
    async for session in get_session():
        game = await get_game(session, game_id)
        
        await callback.message.edit_text(
            f"🎮 Гра: <b>{game.name}</b>\n"
            f"📅 Дата: {data['date'].strftime('%d.%m.%Y')}\n"
            f"⏰ Час: {data['start_time']} - {data['end_time']}\n\n"
            f"💳 Оберіть тип оплати для цієї сесії:",
            reply_markup=keyboard,
            parse_mode="HTML"
        )
    
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
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Список гравців",
                    callback_data=f"admin_players_list_{session_id}"
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


# ===== ЗАПОВНЕННЯ ТЕСТОВИМИ ІГРАМИ =====

@router.message(F.text == "🎲 Заповнити тестовими іграми")
@admin_only
async def populate_test_games(message: Message):
    """Заповнити базу тестовими іграми"""
    await message.answer("🎮 Запускаю заповнення тестовими іграми...")
    
    try:
        # Список тестових ігор
        TEST_GAMES = [
            {
                "name": "Катан",
                "description": "Економічна стратегія про колонізацію острова. Будуйте поселення, торгуйте ресурсами та розвивайте свою цивілізацію.",
                "min_players": 3,
                "max_players": 4,
                "avg_duration": 90
            },
            {
                "name": "Каркассон",
                "description": "Стратегічна гра про будівництво середньовічного французького міста за допомогою тайлів. Розміщуйте своїх міплів і набирайте очки.",
                "min_players": 2,
                "max_players": 5,
                "avg_duration": 45
            },
            {
                "name": "Пандемія",
                "description": "Кооперативна гра, де команда лікарів бореться проти чотирьох смертельних хвороб. Працюйте разом, щоб врятувати людство!",
                "min_players": 2,
                "max_players": 4,
                "avg_duration": 60
            },
            {
                "name": "Азул",
                "description": "Абстрактна гра про викладку плиток з красивими візерунками. Створюйте гармонійні композиції та набирайте очки.",
                "min_players": 2,
                "max_players": 4,
                "avg_duration": 45
            },
            {
                "name": "Вінгспан",
                "description": "Стратегічна гра про спостереження за птахами. Будуйте заповідники, годуйте птахів та збирайте колекції.",
                "min_players": 1,
                "max_players": 5,
                "avg_duration": 75
            },
            {
                "name": "Скривлені кубики",
                "description": "Креативна гра про будівництво веж з кубиків. Використовуйте фізику та логіку для створення стабільних конструкцій.",
                "min_players": 1,
                "max_players": 8,
                "avg_duration": 30
            },
            {
                "name": "Тікет до їзди",
                "description": "Стратегічна гра про будівництво залізниць по Європі. Плануйте маршрути та з'єднуйте міста.",
                "min_players": 2,
                "max_players": 5,
                "avg_duration": 60
            },
            {
                "name": "Сетлс оф Катан",
                "description": "Класична стратегічна гра про колонізацію острова. Торгуйте ресурсами та будьте першим до перемоги.",
                "min_players": 3,
                "max_players": 4,
                "avg_duration": 90
            },
            {
                "name": "Каркуссон",
                "description": "Стратегічна гра про будівництво середньовічного міста. Розміщуйте тайли та своїх міплів для набору очок.",
                "min_players": 2,
                "max_players": 5,
                "avg_duration": 45
            },
            {
                "name": "Домініон",
                "description": "Карткова гра про будівництво королівства. Купуйте картки та створюйте потужні комбінації.",
                "min_players": 2,
                "max_players": 4,
                "avg_duration": 30
            },
            {
                "name": "7 Чудес",
                "description": "Стратегічна гра про будівництво античних чудес світу. Розвивайте цивілізацію та змагайтеся з сусідами.",
                "min_players": 2,
                "max_players": 7,
                "avg_duration": 30
            },
            {
                "name": "Сплінтер",
                "description": "Кооперативна гра про виживання в підземеллі. Досліджуйте, збирайте ресурси та уникайте небезпек.",
                "min_players": 1,
                "max_players": 4,
                "avg_duration": 90
            },
            {
                "name": "Глоріа Мундіс",
                "description": "Стратегічна гра про будівництво середньовічного монастиря. Керуйте ресурсами та розвивайте духовність.",
                "min_players": 1,
                "max_players": 4,
                "avg_duration": 75
            },
            {
                "name": "Терраформінг Марс",
                "description": "Стратегічна гра про колонізацію Марса. Підвищуйте температуру, додавайте кисень та створюйте океани.",
                "min_players": 1,
                "max_players": 5,
                "avg_duration": 120
            },
            {
                "name": "Еверделл",
                "description": "Стратегічна гра про будівництво міста тварин. Збирайте ресурси, будьте споруди та розвивайте свою цивілізацію.",
                "min_players": 1,
                "max_players": 4,
                "avg_duration": 80
            },
            {
                "name": "Розумні Сіті",
                "description": "Стратегічна гра про будівництво сучасного міста. Плануйте квартали, розвивайте інфраструктуру та залучайте жителів.",
                "min_players": 1,
                "max_players": 4,
                "avg_duration": 75
            },
            {
                "name": "Король Нью-Йорка",
                "description": "Стратегічна гра про боротьбу монстрів за контроль над Нью-Йорком. Знищуйте будівлі та станьте королем міста.",
                "min_players": 2,
                "max_players": 6,
                "avg_duration": 115
            }
        ]
        
        # Перевіряємо чи вже є ігри
        async for session in get_session():
            existing_games = await GameService.get_all_active_games(session)
            if existing_games:
                await message.answer(f"⚠️ В базі вже є {len(existing_games)} ігор. Пропускаємо заповнення.")
                return
            
            # Додаємо ігри
            added_count = 0
            for game_data in TEST_GAMES:
                try:
                    game = await GameService.create_new_game(
                        session=session,
                        name=game_data["name"],
                        description=game_data["description"],
                        min_players=game_data["min_players"],
                        max_players=game_data["max_players"],
                        avg_duration=game_data["avg_duration"],
                        image_path=None
                    )
                    added_count += 1
                except Exception as e:
                    await message.answer(f"❌ Помилка при додаванні {game_data['name']}: {e}")
            
            await message.answer(f"✅ Успішно додано {added_count} з {len(TEST_GAMES)} тестових ігор!")
            break
        
    except Exception as e:
        await message.answer(f"❌ Помилка при заповненні: {e}")
        import traceback
        await message.answer(f"Деталі: {traceback.format_exc()}")


# ===== РЕДАГУВАННЯ ІНФОРМАЦІЇ ПРО КЛУБ =====

@router.message(F.text == "ℹ️ Редагувати інформацію про клуб")
@admin_only
async def edit_club_info_start(message: Message, state: FSMContext):
    """Почати редагування інформації про клуб"""
    import config
    from database import get_session, get_setting
    
    # Отримуємо поточні значення з БД
    async for db_session in get_session():
        club_name = await get_setting(db_session, "CLUB_NAME")
        club_description = await get_setting(db_session, "CLUB_DESCRIPTION")
    
    # Використовуємо значення з БД якщо є, якщо немає - з .env
    current_name = club_name or config.CLUB_NAME
    current_description = club_description or config.CLUB_DESCRIPTION
    
    text = "ℹ️ <b>Редагування інформації про клуб</b>\n\n"
    text += f"<b>Поточна назва:</b> {current_name}\n"
    text += f"<b>Поточний опис:</b> {current_description}\n\n"
    text += "Оберіть що хочете редагувати:"
    
    keyboard = [
        [InlineKeyboardButton(text="🏢 Назва клубу", callback_data="edit_club_name")],
        [InlineKeyboardButton(text="📝 Опис клубу", callback_data="edit_club_description")],
        [InlineKeyboardButton(text="ℹ️ Текст 'Про ігротеку'", callback_data="edit_club_about")],
        [InlineKeyboardButton(text="💳 Інформація про оплату", callback_data="edit_payment_info_menu")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ]
    
    await message.answer(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit_club_name")
@admin_only
async def edit_club_name_start(callback: CallbackQuery, state: FSMContext):
    """Почати редагування назви клубу"""
    await state.set_state(EditClubInfoStates.waiting_for_name)
    
    await callback.message.edit_text(
        "📝 <b>Редагування назви клубу</b>\n\n"
        "Надішліть нову назву клубу:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditClubInfoStates.waiting_for_name)
@admin_only
async def edit_club_name_process(message: Message, state: FSMContext):
    """Обробити нову назву клубу"""
    new_name = message.text.strip()
    
    if len(new_name) < 2:
        await message.answer("❌ Назва клубу має бути довшою за 2 символи.")
        return
    
    if len(new_name) > 100:
        await message.answer("❌ Назва клубу не може бути довшою за 100 символів.")
        return
    
    # Зберігаємо в базі даних
    from database import get_session, set_setting
    async for db_session in get_session():
        await set_setting(db_session, "CLUB_NAME", new_name)
    
    await state.clear()
    await message.answer(
        f"✅ Назву клубу оновлено на: <b>{new_name}</b>\n\n"
        "ℹ️ Зміни застосовано без перезапуску бота.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit_club_description")
@admin_only
async def edit_club_description_start(callback: CallbackQuery, state: FSMContext):
    """Почати редагування опису клубу"""
    await state.set_state(EditClubInfoStates.waiting_for_description)
    
    await callback.message.edit_text(
        "📄 <b>Редагування опису клубу</b>\n\n"
        "Надішліть новий опис клубу:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditClubInfoStates.waiting_for_description)
@admin_only
async def edit_club_description_process(message: Message, state: FSMContext):
    """Обробити новий опис клубу"""
    new_description = message.text.strip()
    
    if len(new_description) < 10:
        await message.answer("❌ Опис клубу має бути довшим за 10 символів.")
        return
    
    if len(new_description) > 500:
        await message.answer("❌ Опис клубу не може бути довшим за 500 символів.")
        return
    
    # Зберігаємо в базі даних
    from database import get_session, set_setting
    async for db_session in get_session():
        await set_setting(db_session, "CLUB_DESCRIPTION", new_description)
    
    await state.clear()
    await message.answer(
        f"✅ Опис клубу оновлено:\n\n<b>{new_description}</b>\n\n"
        "ℹ️ Зміни застосовано без перезапуску бота.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit_club_about")
@admin_only
async def edit_club_about_start(callback: CallbackQuery, state: FSMContext):
    """Почати редагування тексту 'Про ігротеку'"""
    await state.set_state(EditClubInfoStates.waiting_for_about_text)
    
    await callback.message.edit_text(
        "ℹ️ <b>Редагування тексту 'Про ігротеку'</b>\n\n"
        "Надішліть новий повний текст для сторінки 'Про ігротеку':",
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "edit_payment_info_menu")
@admin_only
async def edit_payment_info_menu(callback: CallbackQuery):
    """Меню редагування інформації про оплату"""
    from database import get_session, get_setting
    
    # Отримуємо поточні значення з БД
    async for db_session in get_session():
        payment_info = await get_setting(db_session, "PAYMENT_INFO")
        payment_card = await get_setting(db_session, "PAYMENT_CARD_NUMBER")
        payment_link = await get_setting(db_session, "PAYMENT_BANK_LINK")
    
    text = "💳 <b>Редагування інформації про оплату</b>\n\n"
    text += f"<b>Поточна інформація:</b>\n"
    text += f"• Текст: {'Встановлено' if payment_info else 'Не встановлено'}\n"
    text += f"• Номер картки: {payment_card or 'Не встановлено'}\n"
    text += f"• Посилання на банку: {payment_link or 'Не встановлено'}\n\n"
    text += "Оберіть що хочете редагувати:"
    
    keyboard = [
        [InlineKeyboardButton(text="📝 Текст інформації про оплату", callback_data="edit_payment_text")],
        [InlineKeyboardButton(text="💳 Номер картки", callback_data="edit_card_number")],
        [InlineKeyboardButton(text="🔗 Посилання на банку", callback_data="edit_bank_link")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_club_info")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()


@router.callback_query(F.data == "back_to_club_info")
@admin_only
async def back_to_club_info(callback: CallbackQuery):
    """Повернутися до меню редагування клубу"""
    import config
    from database import get_session, get_setting
    
    # Отримуємо поточні значення з БД
    async for db_session in get_session():
        club_name = await get_setting(db_session, "CLUB_NAME")
        club_description = await get_setting(db_session, "CLUB_DESCRIPTION")
    
    # Використовуємо значення з БД якщо є, якщо немає - з .env
    current_name = club_name or config.CLUB_NAME
    current_description = club_description or config.CLUB_DESCRIPTION
    
    text = "ℹ️ <b>Редагування інформації про клуб</b>\n\n"
    text += f"<b>Поточна назва:</b> {current_name}\n"
    text += f"<b>Поточний опис:</b> {current_description}\n\n"
    text += "Оберіть що хочете редагувати:"
    
    keyboard = [
        [InlineKeyboardButton(text="🏢 Назва клубу", callback_data="edit_club_name")],
        [InlineKeyboardButton(text="📝 Опис клубу", callback_data="edit_club_description")],
        [InlineKeyboardButton(text="ℹ️ Текст 'Про ігротеку'", callback_data="edit_club_about")],
        [InlineKeyboardButton(text="💳 Інформація про оплату", callback_data="edit_payment_info_menu")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="admin_back")]
    ]
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditClubInfoStates.waiting_for_about_text)
@admin_only
async def edit_club_about_process(message: Message, state: FSMContext):
    """Обробити новий текст 'Про ігротеку'"""
    new_about_text = message.text.strip()
    
    if len(new_about_text) < 20:
        await message.answer("❌ Текст має бути довшим за 20 символів.")
        return
    
    if len(new_about_text) > 1000:
        await message.answer("❌ Текст не може бути довшим за 1000 символів.")
        return
    
    # Зберігаємо в базі даних
    from database import get_session, set_setting
    async for db_session in get_session():
        await set_setting(db_session, "CLUB_ABOUT_TEXT", new_about_text)
    
    await state.clear()
    await message.answer(
        f"✅ Текст 'Про ігротеку' оновлено:\n\n<b>{new_about_text}</b>\n\n"
        "ℹ️ Зміни застосовано без перезапуску бота.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit_payment_text")
@admin_only
async def edit_payment_text_start(callback: CallbackQuery, state: FSMContext):
    """Почати редагування тексту про оплату"""
    await state.set_state(EditClubInfoStates.waiting_for_payment_info)
    await callback.message.edit_text(
        "💳 <b>Редагування тексту про оплату</b>\n\n"
        "Надішліть новий текст інформації про оплату:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditClubInfoStates.waiting_for_payment_info)
@admin_only
async def edit_payment_text_process(message: Message, state: FSMContext):
    """Обробити новий текст про оплату"""
    new_text = message.text.strip()
    
    # Зберігаємо в базі даних
    from database import get_session, set_setting
    async for db_session in get_session():
        await set_setting(db_session, "PAYMENT_INFO", new_text)
    
    await state.clear()
    await message.answer(
        f"✅ Текст про оплату оновлено!\n\n"
        "ℹ️ Зміни застосовано без перезапуску бота.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit_card_number")
@admin_only
async def edit_card_number_start(callback: CallbackQuery, state: FSMContext):
    """Почати редагування номера картки"""
    await state.set_state(EditClubInfoStates.waiting_for_card_number)
    await callback.message.edit_text(
        "💳 <b>Редагування номера картки</b>\n\n"
        "Надішліть номер картки:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditClubInfoStates.waiting_for_card_number)
@admin_only
async def edit_card_number_process(message: Message, state: FSMContext):
    """Обробити новий номер картки"""
    new_card = message.text.strip()
    
    # Зберігаємо в базі даних
    from database import get_session, set_setting
    async for db_session in get_session():
        await set_setting(db_session, "PAYMENT_CARD_NUMBER", new_card)
    
    await state.clear()
    await message.answer(
        f"✅ Номер картки оновлено: <code>{new_card}</code>\n\n"
        "ℹ️ Зміни застосовано без перезапуску бота.",
        parse_mode="HTML"
    )


@router.callback_query(F.data == "edit_bank_link")
@admin_only
async def edit_bank_link_start(callback: CallbackQuery, state: FSMContext):
    """Почати редагування посилання на банку"""
    await state.set_state(EditClubInfoStates.waiting_for_bank_link)
    await callback.message.edit_text(
        "🔗 <b>Редагування посилання на банку</b>\n\n"
        "Надішліть посилання на банку:",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(EditClubInfoStates.waiting_for_bank_link)
@admin_only
async def edit_bank_link_process(message: Message, state: FSMContext):
    """Обробити нове посилання на банку"""
    new_link = message.text.strip()
    
    # Зберігаємо в базі даних
    from database import get_session, set_setting
    async for db_session in get_session():
        await set_setting(db_session, "PAYMENT_BANK_LINK", new_link)
    
    await state.clear()
    await message.answer(
        f"✅ Посилання на банку оновлено: {new_link}\n\n"
        "ℹ️ Зміни застосовано без перезапуску бота.",
        parse_mode="HTML"
    )


# ===== КІК ГРАВЦЯ З СЕСІЇ =====

@router.callback_query(F.data.startswith("admin_players_list_"))
@admin_only
async def admin_show_players_list(callback: CallbackQuery):
    """Показати список гравців для адміна з можливістю кіку"""
    session_id = int(callback.data.split("_")[-1])
    
    async for db_session in get_session():
        # Отримуємо сесію
        from sqlmodel import select
        from database.models import GameSession, User
        
        result = await db_session.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session:
            await callback.answer("Сесію не знайдено", show_alert=True)
            return
        
        # Отримуємо гру
        game = await get_game(db_session, game_session.game_id)
        if not game:
            await callback.answer("Гру не знайдено", show_alert=True)
            return
        
        # Отримуємо реєстрації
        registrations = await get_registrations(db_session, session_id, active_only=True)
        
        text = f"👥 <b>Список гравців (Адмін)</b>\n\n"
        text += f"🎮 Гра: <b>{game.name}</b>\n"
        text += f"📅 Дата: {format_date(game_session.date)}\n"
        text += f"⏰ Час: {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n\n"
        
        if not registrations:
            text += "Поки що ніхто не зареєстрований на цю гру."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin_manage_session_{session_id}")]
            ])
        else:
            text += f"<b>Зареєстровано: {len(registrations)}/{game.max_players}</b>\n\n"
            
            # Отримуємо інформацію про кожного гравця
            keyboard_buttons = []
            for i, reg in enumerate(registrations, 1):
                result = await db_session.execute(
                    select(User).where(User.id == reg.user_id)
                )
                player = result.scalar_one_or_none()
                
                if player:
                    player_name = player.first_name
                    if player.last_name:
                        player_name += f" {player.last_name}"
                    
                    if player.username:
                        text += f"{i}. @{player.username} ({player_name})\n"
                    else:
                        text += f"{i}. {player_name}\n"
                    
                    # Кнопка кіку для кожного гравця
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            text=f"🚫 Кікнути {player_name}",
                            callback_data=f"admin_kick_player_{session_id}_{reg.user_id}"
                        )
                    ])
            
            # Додаємо кнопку назад
            keyboard_buttons.append([
                InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin_manage_session_{session_id}")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
        await callback.message.edit_text(
            text,
            reply_markup=keyboard,
            parse_mode="HTML"
        )
        await callback.answer()


@router.callback_query(F.data.startswith("admin_kick_player_"))
@admin_only
async def admin_kick_player_start(callback: CallbackQuery, state: FSMContext):
    """Почати процес кіку гравця"""
    parts = callback.data.split("_")
    session_id = int(parts[3])
    user_id = int(parts[4])
    
    # Зберігаємо дані в FSM
    await state.update_data(session_id=session_id, user_id=user_id)
    await state.set_state(KickPlayerStates.waiting_for_reason)
    
    await callback.message.edit_text(
        "🚫 <b>Кік гравця з сесії</b>\n\n"
        "Надішліть причину кіку (або напишіть 'пропустити' щоб не вказувати причину):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(KickPlayerStates.waiting_for_reason)
@admin_only
async def admin_kick_player_reason(message: Message, state: FSMContext):
    """Обробити причину кіку"""
    reason = message.text.strip()
    
    if reason.lower() in ['пропустити', 'skip', 'немає', 'без причини']:
        reason = None
    
    await state.update_data(reason=reason)
    await state.set_state(KickPlayerStates.waiting_for_confirmation)
    
    # Отримуємо дані гравця
    data = await state.get_data()
    session_id = data['session_id']
    user_id = data['user_id']
    
    async for db_session in get_session():
        from sqlmodel import select
        from database.models import User, GameSession
        
        # Отримуємо дані гравця
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        player = result.scalar_one_or_none()
        
        # Отримуємо дані сесії
        result = await db_session.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not player or not game_session:
            await message.answer("❌ Помилка: гравець або сесія не знайдені.")
            await state.clear()
            return
        
        # Отримуємо гру
        game = await get_game(db_session, game_session.game_id)
        if not game:
            await message.answer("❌ Помилка: гра не знайдена.")
            await state.clear()
            return
        
        player_name = player.first_name
        if player.last_name:
            player_name += f" {player.last_name}"
        
        text = f"🚫 <b>Підтвердження кіку</b>\n\n"
        text += f"👤 Гравець: <b>{player_name}</b>\n"
        text += f"🎮 Гра: <b>{game.name}</b>\n"
        text += f"📅 Дата: {format_date(game_session.date)}\n"
        text += f"⏰ Час: {format_time(game_session.start_time)}\n\n"
        
        if reason:
            text += f"📝 Причина: <b>{reason}</b>\n\n"
        else:
            text += "📝 Причина: <b>не вказана</b>\n\n"
        
        text += "⚠️ Ви впевнені, що хочете кікнути цього гравця?"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так, кікнути", callback_data="confirm_kick"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_kick")
            ]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "confirm_kick")
@admin_only
async def admin_confirm_kick(callback: CallbackQuery, state: FSMContext):
    """Підтвердити кік гравця"""
    data = await state.get_data()
    session_id = data['session_id']
    user_id = data['user_id']
    reason = data.get('reason')
    
    async for db_session in get_session():
        from sqlmodel import select
        from database.models import User, GameSession, Registration
        
        # Отримуємо дані гравця
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        player = result.scalar_one_or_none()
        
        # Отримуємо дані сесії
        result = await db_session.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not player or not game_session:
            await callback.answer("❌ Помилка: гравець або сесія не знайдені.", show_alert=True)
            await state.clear()
            return
        
        # Отримуємо гру
        game = await get_game(db_session, game_session.game_id)
        if not game:
            await callback.answer("❌ Помилка: гра не знайдена.", show_alert=True)
            await state.clear()
            return
        
        # Знаходимо реєстрацію
        result = await db_session.execute(
            select(Registration).where(
                Registration.session_id == session_id,
                Registration.user_id == user_id,
                Registration.is_active == True
            )
        )
        registration = result.scalar_one_or_none()
        
        if not registration:
            await callback.answer("❌ Помилка: реєстрація не знайдена.", show_alert=True)
            await state.clear()
            return
        
        # Деактивуємо реєстрацію
        registration.is_active = False
        await db_session.commit()
        
        # Надсилаємо повідомлення гравцю
        player_name = player.first_name
        if player.last_name:
            player_name += f" {player.last_name}"
        
        kick_message = f"🚫 <b>Вас кікнули з ігрової сесії</b>\n\n"
        kick_message += f"🎮 Гра: <b>{game.name}</b>\n"
        kick_message += f"📅 Дата: {format_date(game_session.date)}\n"
        kick_message += f"⏰ Час: {format_time(game_session.start_time)}\n\n"
        
        if reason:
            kick_message += f"📝 Причина: <b>{reason}</b>"
        else:
            kick_message += "📝 Причина не вказана"
        
        try:
            from aiogram import Bot
            from config import BOT_TOKEN
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(
                chat_id=player.telegram_id,
                text=kick_message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Помилка надсилання повідомлення гравцю: {e}")
        
        await callback.message.edit_text(
            f"✅ Гравець <b>{player_name}</b> успішно кікнутий з сесії!\n\n"
            f"📨 Повідомлення надіслано гравцю.",
            parse_mode="HTML"
        )
        
        await state.clear()
        await callback.answer()


@router.callback_query(F.data == "cancel_kick")
@admin_only
async def admin_cancel_kick(callback: CallbackQuery, state: FSMContext):
    """Скасувати кік гравця"""
    await callback.message.edit_text("❌ Кік гравця скасовано.")
    await state.clear()
    await callback.answer()


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
        from sqlmodel import select
        from database.models import GameSession, User
        
        # Спочатку отримуємо інформацію про сесію та гравців для сповіщення
        result = await db_session.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session:
            await callback.answer("❌ Сесію не знайдено", show_alert=True)
            return
        
        # Отримуємо гру
        game = await get_game(db_session, game_session.game_id)
        if not game:
            await callback.answer("❌ Гру не знайдено", show_alert=True)
            return
        
        # Отримуємо всіх зареєстрованих гравців
        registrations = await get_registrations(db_session, session_id, active_only=True)
        
        # Зберігаємо інформацію про гравців для сповіщення
        players_to_notify = []
        for reg in registrations:
            result = await db_session.execute(
                select(User).where(User.id == reg.user_id)
            )
            player = result.scalar_one_or_none()
            if player:
                players_to_notify.append(player)
        
        # Видаляємо сесію (це також видалить всі реєстрації)
        success = await ScheduleService.delete_session(db_session, session_id)
        
        if success:
            # Сповіщаємо всіх зареєстрованих гравців
            if players_to_notify:
                from aiogram import Bot
                from config import BOT_TOKEN
                bot = Bot(token=BOT_TOKEN)
                
                notification_text = f"❌ <b>Сесію гри скасовано</b>\n\n"
                notification_text += f"🎮 Гра: <b>{game.name}</b>\n"
                notification_text += f"📅 Дата: {format_date(game_session.date)}\n"
                notification_text += f"⏰ Час: {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n\n"
                notification_text += "Вибачте за незручності. Слідкуйте за оновленнями розкладу."
                
                for player in players_to_notify:
                    try:
                        await bot.send_message(
                            chat_id=player.telegram_id,
                            text=notification_text,
                            parse_mode="HTML"
                        )
                    except Exception as e:
                        print(f"Помилка надсилання повідомлення гравцю {player.telegram_id}: {e}")
            
            text = "✅ Сесію успішно видалено!"
            if players_to_notify:
                text += f"\n📨 Сповіщення надіслано {len(players_to_notify)} гравцям."
            
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
