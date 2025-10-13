from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import date

from database import get_session, get_user_by_telegram_id
from services import ScheduleService, RegistrationService, GameService, NotificationService
from keyboards import get_schedule_keyboard, get_game_actions_keyboard, get_my_registrations_keyboard
from utils.helpers import format_date, format_time
from database.crud import get_game, get_registrations

router = Router()


@router.message(F.text == "📅 Розклад ігор")
async def show_schedule(message: Message):
    """Показати розклад ігор"""
    async for session in get_session():
        # Отримуємо майбутні сесії
        sessions = await ScheduleService.get_upcoming_schedule(session, days=7)
        
        if not sessions:
            await message.answer(
                "📅 На найближчі 7 днів немає запланованих ігор.\n\n"
                "Слідкуйте за оновленнями!"
            )
            return
        
        # Групуємо по датах
        grouped = await ScheduleService.group_sessions_by_date(sessions)
        
        text = "📅 <b>Розклад ігор на найближчі 7 днів:</b>\n\n"
        text += "Оберіть дату, щоб переглянути ігри:"
        
        # Створюємо клавіатуру з датами
        keyboard = []
        for session_date, date_sessions in grouped.items():
            date_str = format_date(session_date)
            keyboard.append([{
                "text": f"📅 {date_str} ({len(date_sessions)} ігор)",
                "callback_data": f"schedule_date_{session_date.isoformat()}"
            }])
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
            for row in keyboard for btn in row
        ])
        
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("schedule_date_"))
async def show_date_sessions(callback: CallbackQuery):
    """Показати ігри на обрану дату"""
    date_str = callback.data.split("_")[-1]
    selected_date = date.fromisoformat(date_str)
    
    async for session in get_session():
        # Отримуємо сесії на цю дату
        sessions = await ScheduleService.get_sessions_by_period(
            session, from_date=selected_date, to_date=selected_date
        )
        
        if not sessions:
            await callback.answer("На цю дату немає ігор", show_alert=True)
            return
        
        # Отримуємо ціни на цей день
        from database import get_day_pricing
        day_pricing = await get_day_pricing(session, selected_date)
        
        text = f"📅 <b>{format_date(selected_date)}</b>\n\n"
        
        # Показуємо ціни на день
        if day_pricing:
            text += f"💰 <b>Вхід на день:</b>\n"
            text += f"   • Дорослі: {day_pricing.adult_price} грн\n"
            text += f"   • Діти до 18: {day_pricing.child_price} грн\n\n"
        
        text += "<b>Ігрові сесії:</b>\n"
        
        # Створюємо клавіатуру з іграми
        keyboard = []
        for game_session in sessions:
            game = await get_game(session, game_session.game_id)
            if not game:
                continue
            
            registrations = await get_registrations(session, game_session.id, active_only=True)
            players_count = len(registrations)
            
            # Додаємо іконку типу оплати
            payment_icon = {
                "included": "✅",
                "free": "🎁",
                "donate": "💝"
            }
            
            game_info = f"{payment_icon.get(game_session.payment_type, '✅')} {game.name} • {format_time(game_session.start_time)}"
            game_info += f" • {players_count}/{game.max_players}"
            
            keyboard.append([{
                "text": game_info,
                "callback_data": f"view_session_{game_session.id}"
            }])
        
        keyboard.append([{"text": "🔙 Назад до дат", "callback_data": "back_to_schedule"}])
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
            for row in keyboard for btn in row
        ])
        
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("view_session_"))
async def view_session_details(callback: CallbackQuery):
    """Переглянути детальну інформацію про сесію"""
    session_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    
    async for db_session in get_session():
        # Отримуємо сесію
        from sqlmodel import select
        from database.models import GameSession
        
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
        players_count = len(registrations)
        
        # Перевіряємо, чи зареєстрований користувач
        user = await get_user_by_telegram_id(db_session, user_id)
        is_registered = False
        is_admin = False
        if user:
            is_registered = await RegistrationService.is_user_registered(
                db_session, user.id, session_id
            )
            is_admin = user.is_admin
        
        # Отримуємо ціни на день
        from database import get_day_pricing
        day_pricing = await get_day_pricing(db_session, game_session.date)
        
        # Формуємо текст
        text = f"🎮 <b>{game.name}</b>\n\n"
        text += f"📝 {game.description}\n\n"
        text += f"📅 <b>Дата:</b> {format_date(game_session.date)}\n"
        text += f"⏰ <b>Час:</b> {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n"
        text += f"👥 <b>Гравців:</b> {game.min_players}-{game.max_players}\n"
        text += f"⏱️ <b>Тривалість:</b> ~{game.avg_duration} хв\n\n"
        
        # Показуємо ціни на день
        if day_pricing:
            text += f"💰 <b>Вхід на день:</b>\n"
            text += f"   • Дорослі: {day_pricing.adult_price} грн\n"
            text += f"   • Діти до 18: {day_pricing.child_price} грн\n\n"
        
        # Показуємо тип оплати для сесії
        payment_type_text = {
            "included": "✅ Входить в оплату за вхід",
            "free": "🎁 Безкоштовна",
            "donate": "💝 Free donate"
        }
        text += f"💳 <b>Оплата гри:</b> {payment_type_text.get(game_session.payment_type, 'Входить в оплату')}\n\n"
        
        text += f"📊 <b>Зареєстровано:</b> {players_count}/{game.max_players}\n"
        
        if is_registered:
            text += "\n✅ <b>Ви зареєстровані на цю гру</b>"
        
        # Клавіатура
        keyboard = get_game_actions_keyboard(session_id, is_registered, is_admin=is_admin)
        
        # Перевіряємо чи це повідомлення з фото
        has_photo = callback.message.photo is not None and len(callback.message.photo) > 0
        
        # Відправляємо з фото якщо воно є
        if game.image_path and not has_photo:
            from aiogram.types import FSInputFile
            import os
            
            # Якщо файл існує і це перший показ - відправляємо нове повідомлення з фото
            if os.path.exists(game.image_path):
                await callback.message.delete()
                photo = FSInputFile(game.image_path)
                await callback.message.answer_photo(
                    photo=photo,
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            else:
                # Якщо файл не існує, просто редагуємо текст
                try:
                    await callback.message.edit_text(
                        text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                except:
                    pass
        elif has_photo:
            # Якщо вже є фото, оновлюємо caption
            try:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            # Якщо немає зображення, просто редагуємо текст
            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except:
                pass
        
        await callback.answer()


@router.callback_query(F.data.startswith("register_"))
async def register_for_game(callback: CallbackQuery):
    """Зареєструватися на гру"""
    session_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    
    async for db_session in get_session():
        # Отримуємо користувача
        user = await get_user_by_telegram_id(db_session, user_id)
        if not user:
            await callback.answer("Помилка: користувача не знайдено", show_alert=True)
            return
        
        # Реєструємо
        success, message = await RegistrationService.register_user(
            db_session, user.id, session_id
        )
        
        if success:
            # Отримуємо сесію для сповіщень
            from sqlmodel import select
            from database.models import GameSession
            
            result = await db_session.execute(
                select(GameSession).where(GameSession.id == session_id)
            )
            game_session = result.scalar_one_or_none()
            
            if game_session:
                # Відправляємо сповіщення адміністраторам
                from aiogram import Bot
                bot = callback.bot
                await NotificationService.notify_admins_new_registration(
                    bot, db_session, game_session, user
                )
            
            # Відправляємо повідомлення про успіх
            await callback.answer(message, show_alert=True)
            
            # Показуємо оновлену інформацію про сесію
            # Створюємо новий callback з правильним session_id
            from aiogram.types import CallbackQuery as CQ
            new_callback = CQ(
                id=callback.id,
                from_user=callback.from_user,
                message=callback.message,
                chat_instance=callback.chat_instance,
                data=f"view_session_{session_id}"
            )
            await view_session_details(new_callback)
        else:
            await callback.answer(message, show_alert=True)


@router.callback_query(F.data.startswith("unregister_"))
async def unregister_from_game(callback: CallbackQuery):
    """Скасувати реєстрацію на гру"""
    session_id = int(callback.data.split("_")[-1])
    user_id = callback.from_user.id
    
    async for db_session in get_session():
        # Отримуємо користувача
        user = await get_user_by_telegram_id(db_session, user_id)
        if not user:
            await callback.answer("Помилка: користувача не знайдено", show_alert=True)
            return
        
        # Отримуємо сесію для сповіщення
        from sqlmodel import select
        from database.models import GameSession
        
        result = await db_session.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        game_session = result.scalar_one_or_none()
        
        # Скасовуємо реєстрацію
        success, message = await RegistrationService.unregister_user(
            db_session, user.id, session_id
        )
        
        if success:
            # Відправляємо сповіщення адміністраторам
            if game_session:
                from aiogram import Bot
                bot = callback.bot
                await NotificationService.notify_admins_cancellation(
                    bot, db_session, game_session, user
                )
            
            await callback.answer(message, show_alert=True)
            
            # Показуємо оновлену інформацію про сесію
            from aiogram.types import CallbackQuery as CQ
            new_callback = CQ(
                id=callback.id,
                from_user=callback.from_user,
                message=callback.message,
                chat_instance=callback.chat_instance,
                data=f"view_session_{session_id}"
            )
            await view_session_details(new_callback)
        else:
            await callback.answer(message, show_alert=True)


@router.message(F.text == "🎮 Мої записи")
async def show_my_registrations(message: Message):
    """Показати записи користувача"""
    user_id = message.from_user.id
    
    async for db_session in get_session():
        # Отримуємо користувача
        user = await get_user_by_telegram_id(db_session, user_id)
        if not user:
            await message.answer("Помилка: користувача не знайдено")
            return
        
        # Отримуємо реєстрації
        registrations = await RegistrationService.get_user_active_registrations(
            db_session, user.id
        )
        
        # Форматуємо список
        text = await RegistrationService.format_registrations_list(db_session, registrations)
        
        # Фільтруємо тільки майбутні сесії для кнопок
        from sqlmodel import select
        from database.models import GameSession
        from datetime import date
        
        today = date.today()
        future_registrations = []
        
        for reg in registrations:
            result = await db_session.execute(
                select(GameSession).where(GameSession.id == reg.session_id)
            )
            game_session = result.scalar_one_or_none()
            
            if game_session and game_session.date >= today:
                future_registrations.append(reg)
        
        if future_registrations:
            # Створюємо клавіатуру тільки для майбутніх сесій
            keyboard = []
            for reg in future_registrations:
                keyboard.append([{
                    "text": f"Переглянути сесію #{reg.session_id}",
                    "callback_data": f"view_session_{reg.session_id}"
                }])
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
                for row in keyboard for btn in row
            ])
            
            await message.answer(text, reply_markup=kb, parse_mode="HTML")
        else:
            await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data.startswith("players_list_"))
async def show_players_list(callback: CallbackQuery):
    """Показати список зареєстрованих гравців"""
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
        
        text = f"👥 <b>Список гравців</b>\n\n"
        text += f"🎮 Гра: <b>{game.name}</b>\n"
        text += f"📅 Дата: {format_date(game_session.date)}\n"
        text += f"⏰ Час: {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n\n"
        
        if not registrations:
            text += "Поки що ніхто не зареєстрований на цю гру."
        else:
            text += f"<b>Зареєстровано: {len(registrations)}/{game.max_players}</b>\n\n"
            
            # Отримуємо інформацію про кожного гравця
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
        
        # Кнопка назад
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=f"view_session_{session_id}")]
        ])
        
        # Перевіряємо чи це повідомлення з фото
        has_photo = callback.message.photo is not None and len(callback.message.photo) > 0
        
        if has_photo:
            # Якщо є фото, оновлюємо caption
            try:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except:
                pass
        else:
            # Якщо немає фото, оновлюємо текст
            try:
                await callback.message.edit_text(
                    text,
                    reply_markup=keyboard,
                    parse_mode="HTML"
                )
            except:
                pass
        
        await callback.answer()


@router.callback_query(F.data == "back_to_schedule")
async def back_to_schedule(callback: CallbackQuery):
    """Повернутися до розкладу"""
    # Просто викликаємо показ розкладу
    await callback.message.delete()
    await show_schedule(callback.message)


@router.callback_query(F.data == "no_games")
async def no_games_callback(callback: CallbackQuery):
    """Обробник для кнопки 'Немає доступних ігор'"""
    await callback.answer("На жаль, поки немає доступних ігор 🎮", show_alert=True)


@router.callback_query(F.data == "no_registrations")
async def no_registrations_callback(callback: CallbackQuery):
    """Обробник для кнопки 'Немає активних записів'"""
    await callback.answer("У вас поки немає активних записів на ігри", show_alert=True)


@router.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback: CallbackQuery):
    """Повернутися до головного меню"""
    await callback.message.delete()
    await callback.answer()
