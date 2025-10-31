from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from keyboards import get_main_menu
from config import ADMIN_IDS
import os

router = Router()


@router.message(F.text == "🏠 Головне меню")
async def back_to_menu(message: Message):
    """Повернення до головного меню"""
    is_admin = message.from_user.id in ADMIN_IDS
    
    await message.answer(
        "🏠 Головне меню",
        reply_markup=get_main_menu(is_admin=is_admin)
    )


@router.message(F.text == "ℹ️ Про ігротеку")
async def about_club(message: Message):
    """Інформація про ігротеку"""
    import config
    from database import get_session, get_setting
    
    # Спочатку намагаємося отримати з БД
    async for session in get_session():
        club_about_text = await get_setting(session, "CLUB_ABOUT_TEXT")
        club_name = await get_setting(session, "CLUB_NAME")
        club_description = await get_setting(session, "CLUB_DESCRIPTION")
    
    if club_about_text:
        # Використовуємо текст з БД
        about_text = club_about_text
    else:
        # Використовуємо стандартний текст з .env або дефолтний
        display_name = club_name or config.CLUB_NAME
        display_description = club_description or config.CLUB_DESCRIPTION
        
        about_text = f"ℹ️ <b>{display_name}</b>\n\n"
        about_text += f"{display_description}\n\n"
        about_text += "🎲 У нас ви можете:\n"
        about_text += "• Грати в настільні ігри\n"
        about_text += "• Знайомитися з новими людьми\n"
        about_text += "• Відкривати для себе нові ігри\n"
        about_text += "• Весело проводити час\n\n"
        about_text += "📅 Слідкуйте за розкладом і записуйтесь на ігри через бота!"
    
    await message.answer(about_text, parse_mode="HTML")


@router.message(F.text == "🏆 Топ-10 ігротеки")
async def show_top_players(message: Message):
    """Показати топ-10 гравців за кількістю відвіданих сесій та подій"""
    from database import get_session
    from sqlalchemy import select, func, case
    from database.models import User, Registration, GameSession, EventRegistration, Event
    from datetime import date
    
    async for session in get_session():
        today = date.today()
        
        # Підзапит для підрахунку ігрових сесій
        game_sessions_subquery = (
            select(
                Registration.user_id,
                func.count(func.distinct(GameSession.id)).label('game_sessions_count')
            )
            .join(GameSession, Registration.session_id == GameSession.id)
            .where(
                Registration.is_active.is_(True),
                GameSession.date < today
            )
            .group_by(Registration.user_id)
            .subquery()
        )
        
        # Підзапит для підрахунку подій
        events_subquery = (
            select(
                EventRegistration.user_id,
                func.count(func.distinct(Event.id)).label('events_count')
            )
            .join(Event, EventRegistration.event_id == Event.id)
            .where(
                EventRegistration.is_active.is_(True),
                Event.date < today
            )
            .group_by(EventRegistration.user_id)
            .subquery()
        )
        
        # Основний запит, що об'єднує обидва підзапити
        result = await session.execute(
            select(
                User.id,
                User.telegram_id,
                User.username,
                User.first_name,
                User.last_name,
                func.coalesce(game_sessions_subquery.c.game_sessions_count, 0).label('game_sessions_count'),
                func.coalesce(events_subquery.c.events_count, 0).label('events_count')
            )
            .outerjoin(game_sessions_subquery, User.id == game_sessions_subquery.c.user_id)
            .outerjoin(events_subquery, User.id == events_subquery.c.user_id)
            .where(
                (game_sessions_subquery.c.game_sessions_count.isnot(None)) |
                (events_subquery.c.events_count.isnot(None))
            )
            .order_by(
                (func.coalesce(game_sessions_subquery.c.game_sessions_count, 0) + 
                 func.coalesce(events_subquery.c.events_count, 0)).desc()
            )
            .limit(10)
        )
        
        top_users = result.all()
        
        if not top_users:
            await message.answer(
                "🏆 <b>Топ-10 ігротеки</b>\n\n"
                "Поки що немає статистики відвідування сесій та подій.\n\n"
                "Записуйтесь на ігри та події, щоб потрапити в топ!",
                parse_mode="HTML"
            )
            return
        
        text = "🏆 <b>Топ-10 ігротеки</b>\n\n"
        text += "Найактивніші гравці за кількістю відвіданих ігрових сесій та подій:\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user_data in enumerate(top_users, 1):
            medal = medals[i-1] if i <= 3 else f"{i}."
            
            name = user_data.first_name
            if user_data.last_name:
                name += f" {user_data.last_name}"
            
            username_str = f"@{user_data.username}" if user_data.username else name
            game_sessions_count = user_data.game_sessions_count or 0
            events_count = user_data.events_count or 0
            total_count = game_sessions_count + events_count
            
            # Формуємо детальну статистику
            details = []
            if game_sessions_count > 0:
                details.append(f"{game_sessions_count} ігор")
            if events_count > 0:
                details.append(f"{events_count} подій")
            
            details_str = " + ".join(details) if details else "0 активності"
            
            text += f"{medal} <b>{username_str}</b> — {total_count} ({details_str})\n"
        
        text += "\n💡 Відвідуйте більше ігор та подій, щоб потрапити в топ!"
        
        await message.answer(text, parse_mode="HTML")


@router.message(F.text == "🎲 База ігор")
async def show_game_database(message: Message):
    """Показати базу ігор"""
    from database import get_session
    from services import GameService
    
    async for session in get_session():
        games = await GameService.get_all_active_games(session)
        
        if not games:
            await message.answer(
                "🎲 <b>База ігор</b>\n\n"
                "Наразі база ігор порожня.\n\n"
                "Слідкуйте за оновленнями!",
                parse_mode="HTML"
            )
            return
        
        # Показуємо першу сторінку списку ігор
        await show_games_database_page(message, session, page=0)


async def show_games_database_page(message_or_callback, db_session, page: int = 0):
    """Показати сторінку списку ігор для користувача"""
    from services import GameService
    
    games = await GameService.get_all_active_games(db_session)
    
    if not games:
        text = "🎲 <b>База ігор</b>\n\nНаразі база ігор порожня."
        keyboard = InlineKeyboardMarkup(inline_keyboard=[])
        
        if isinstance(message_or_callback, Message):
            await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            await message_or_callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        return
    
    # Обчислюємо пагінацію
    items_per_page = 7
    start_idx = page * items_per_page
    end_idx = start_idx + items_per_page
    total_pages = (len(games) + items_per_page - 1) // items_per_page
    
    text = f"🎲 <b>База ігор</b> (Сторінка {page + 1}/{total_pages})\n\n"
    text += "Оберіть гру для перегляду детальної інформації:"
    
    # Створюємо клавіатуру з іграми
    keyboard_buttons = []
    page_games = games[start_idx:end_idx]
    
    for game in page_games:
        keyboard_buttons.append([
            InlineKeyboardButton(
                text=f"🎮 {game.name}",
                callback_data=f"user_view_game_{game.id}"
            )
        ])
    
    # Додаємо кнопки пагінації
    if total_pages > 1:
        pagination_row = []
        
        if page > 0:
            pagination_row.append(
                InlineKeyboardButton(
                    text="◀️ Попередня",
                    callback_data=f"user_games_page_{page-1}"
                )
            )
        
        if page < total_pages - 1:
            pagination_row.append(
                InlineKeyboardButton(
                    text="Наступна ▶️",
                    callback_data=f"user_games_page_{page+1}"
                )
            )
        
        if pagination_row:
            keyboard_buttons.append(pagination_row)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
    
    if isinstance(message_or_callback, Message):
        await message_or_callback.answer(text, reply_markup=keyboard, parse_mode="HTML")
    else:
        # Перевіряємо чи є фото в повідомленні
        has_photo = message_or_callback.message.photo is not None
        
        if has_photo:
            # Якщо є фото, видаляємо його і відправляємо нове текстове повідомлення
            try:
                await message_or_callback.message.delete()
                await message_or_callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                pass
        else:
            # Якщо немає фото, редагуємо текст
            try:
                await message_or_callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                pass


@router.callback_query(F.data.startswith("user_games_page_"))
async def handle_user_games_pagination(callback: CallbackQuery):
    """Обробка пагінації списку ігор для користувача"""
    page = int(callback.data.split("_")[-1])
    
    from database import get_session
    async for session in get_session():
        await show_games_database_page(callback, session, page=page)
    
    await callback.answer()


@router.callback_query(F.data.startswith("user_view_game_"))
async def user_view_game_details(callback: CallbackQuery):
    """Показати детальну інформацію про гру"""
    game_id = int(callback.data.split("_")[-1])
    
    from database import get_session
    from services import GameService
    
    async for session in get_session():
        game = await GameService.get_game_by_id(session, game_id)
        
        if not game:
            await callback.answer("❌ Гру не знайдено", show_alert=True)
            return
        
        # Формуємо текст з інформацією про гру
        text = f"🎮 <b>{game.name}</b>\n\n"
        text += f"📝 <b>Опис:</b>\n{game.description}\n\n"
        text += f"👥 <b>Кількість гравців:</b> {game.min_players}-{game.max_players}\n"
        text += f"⏱️ <b>Середня тривалість:</b> ~{game.avg_duration} хв\n"
        
        # Кнопка повернення назад
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад до списку", callback_data="user_back_to_games_list")]
        ])
        
        # Перевіряємо чи є зображення (Telegram file_id або локальний файл)
        has_image = game.image_file_id or (game.image_path and os.path.exists(game.image_path))
        
        # Перевіряємо чи поточне повідомлення містить фото
        has_photo = callback.message.photo is not None
        
        if has_image:
            if has_photo:
                # Якщо вже є фото, оновлюємо caption
                try:
                    await callback.message.edit_caption(
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                except Exception:
                    # Якщо не вдалося оновити, видаляємо і відправляємо нове
                    try:
                        await callback.message.delete()
                        
                        if game.image_file_id:
                            await callback.message.answer_photo(
                                photo=game.image_file_id,
                                caption=text,
                                reply_markup=keyboard,
                                parse_mode="HTML"
                            )
                        elif game.image_path:
                            from aiogram.types import FSInputFile
                            photo = FSInputFile(game.image_path)
                            await callback.message.answer_photo(
                                photo=photo,
                                caption=text,
                                reply_markup=keyboard,
                                parse_mode="HTML"
                            )
                    except Exception:
                        pass
            else:
                # Якщо немає фото, відправляємо нове фото з підписом
                try:
                    await callback.message.delete()
                    
                    if game.image_file_id:
                        await callback.message.answer_photo(
                            photo=game.image_file_id,
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                    elif game.image_path:
                        from aiogram.types import FSInputFile
                        photo = FSInputFile(game.image_path)
                        await callback.message.answer_photo(
                            photo=photo,
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                except Exception:
                    # Якщо не вдалося відправити фото, відправляємо тільки текст
                    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            # Якщо немає фото гри
            if has_photo:
                # Якщо є фото, але гри немає фото, видаляємо і відправляємо текст
                try:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                except Exception:
                    pass
            else:
                # Відправляємо тільки текст
                try:
                    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
                except Exception:
                    pass
        
        await callback.answer()


@router.callback_query(F.data == "user_back_to_games_list")
async def user_back_to_games_list(callback: CallbackQuery):
    """Повернутися до списку ігор"""
    from database import get_session
    async for session in get_session():
        await show_games_database_page(callback, session, page=0)
    
    await callback.answer()


@router.message(F.text == "💳 Оплата")
async def show_payment_info(message: Message):
    """Показати інформацію про оплату"""
    import config
    from database import get_session, get_setting
    
    # Отримуємо дані з БД
    async for session in get_session():
        payment_info = await get_setting(session, "PAYMENT_INFO")
        payment_card = await get_setting(session, "PAYMENT_CARD_NUMBER")
        payment_link = await get_setting(session, "PAYMENT_BANK_LINK")
    
    if payment_info:
        # Використовуємо кастомну інформацію з БД
        text = payment_info
    else:
        # Використовуємо стандартну інформацію
        text = "💳 <b>Інформація про оплату</b>\n\n"
        text += "📋 <b>Як це працює:</b>\n"
        text += "• При створенні розкладу адміністратор вказує ціну входу на день\n"
        text += "• Ціна відрізняється для дорослих та дітей до 18 років включно\n"
        text += "• Деякі ігрові сесії можуть бути безкоштовними або за вільну ціну (donate)\n\n"
        
        text += "🎮 <b>Типи оплати для сесій:</b>\n"
        text += "• ✅ - Входить в оплату за вхід\n"
        text += "• 🎁 - Безкоштовна сесія\n"
        text += "• 💝 - Free donate (на ваш розсуд)\n\n"
        
        # Використовуємо дані з БД якщо є, якщо немає - з .env
        card_to_show = payment_card or config.PAYMENT_CARD_NUMBER
        link_to_show = payment_link or config.PAYMENT_BANK_LINK
        
        if card_to_show:
            text += f"💳 <b>Номер картки:</b>\n<code>{card_to_show}</code>\n\n"
        
        if link_to_show:
            text += f"🔗 <b>Посилання на банку:</b>\n{link_to_show}\n\n"
        
        text += "ℹ️ При реєстрації на гру ви побачите вартість входу та умови оплати для кожної сесії."
    
    await message.answer(text, parse_mode="HTML")
