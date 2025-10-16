from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from datetime import date

from database import get_session, get_user_by_telegram_id
from services import ScheduleService, RegistrationService, NotificationService
from keyboards import get_game_actions_keyboard
from utils.helpers import format_date, format_time, format_time_safe
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
        active_sessions_found = False
        
        for game_session in sessions:
            game = await get_game(session, game_session.game_id)
            if not game or not game.is_active:
                continue
            
            active_sessions_found = True
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
            
            # Додаємо контекст дати в callback
            keyboard.append([{
                "text": game_info,
                "callback_data": f"view_session_{game_session.id}_date_{date_str}"
            }])
        
        # Якщо не знайшли активних сесій, показуємо відповідне повідомлення
        if not active_sessions_found:
            text += "На цю дату немає активних ігор"
            keyboard.append([{"text": "🔙 Назад до дат", "callback_data": "back_to_schedule"}])
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
                for row in keyboard for btn in row
            ])
            
            # Перевіряємо, чи повідомлення містить фото
            has_photo = callback.message.photo is not None
            
            if has_photo:
                # Якщо є фото, оновлюємо caption
                try:
                    await callback.message.edit_caption(
                        caption=text,
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    # Якщо не вдалося оновити caption, спробуємо видалити і відправити нове
                    try:
                        await callback.message.delete()
                        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
                    except Exception:
                        pass
            else:
                # Якщо немає фото, редагуємо текст
                try:
                    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
                except Exception as e:
                    # Якщо не вдалося редагувати текст, спробуємо видалити і відправити нове
                    try:
                        await callback.message.delete()
                        await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
                    except Exception:
                        pass
            
            await callback.answer()
            return
        
        keyboard.append([{"text": "🔙 Назад до дат", "callback_data": "back_to_schedule"}])
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
            for row in keyboard for btn in row
        ])
        
        # Перевіряємо, чи повідомлення містить фото
        has_photo = callback.message.photo is not None
        
        if has_photo:
            # Якщо є фото, оновлюємо caption
            try:
                await callback.message.edit_caption(
                    caption=text,
                    reply_markup=kb,
                    parse_mode="HTML"
                )
            except Exception as e:
                # Якщо не вдалося оновити caption, спробуємо видалити і відправити нове
                try:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass
        else:
            # Якщо немає фото, редагуємо текст
            try:
                await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception as e:
                # Якщо не вдалося редагувати текст, спробуємо видалити і відправити нове
                try:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass
        
        await callback.answer()


@router.callback_query(F.data.startswith("view_session_"))
async def view_session_details(callback: CallbackQuery, skip_answer: bool = False):
    """Переглянути детальну інформацію про сесію"""
    # Парсимо callback_data для отримання контексту
    # Формати:
    # - view_session_{id}
    # - view_session_{id}_date_{date_str}
    # - view_session_{id}_my_registrations
    
    parts = callback.data.split("_")
    session_id = int(parts[2])  # view_session_{id}...
    
    # Визначаємо контекст
    context = "schedule"  # за замовчуванням
    date_str = None
    
    if len(parts) > 3:
        if parts[3] == "date" and len(parts) > 4:
            context = "date"
            date_str = parts[4]
        elif parts[3] == "my" and len(parts) > 4 and parts[4] == "registrations":
            context = "my_registrations"
    
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
        if not game or not game.is_active:
            await callback.answer("Гру не знайдено або вона була скасована", show_alert=True)
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
        text += f"📅 <b>Дата:</b> {format_date(game_session.date)}\n"
        text += f"⏰ <b>Час:</b> {format_time_safe(game_session.start_time)} - {format_time_safe(game_session.end_time)}\n"
        text += f"👥 <b>Гравців:</b> {game.min_players}-{game.max_players}\n"
        text += f"⏱️ <b>Тривалість:</b> ~{game.avg_duration} хв\n\n"
        text += f"📝 <b>Опис:</b>\n{game.description}\n\n"
        
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
        
        # Якщо дата не передана в контексті, беремо з сесії
        if not date_str:
            date_str = game_session.date.isoformat()
        
        # Клавіатура з контекстом
        keyboard = get_game_actions_keyboard(
            session_id, is_registered, is_admin=is_admin, 
            context=context, date_str=date_str
        )
        
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
        
        if not skip_answer:
            await callback.answer()


@router.callback_query(F.data.startswith("register_"))
async def register_for_game(callback: CallbackQuery):
    """Зареєструватися на гру"""
    # Парсимо callback_data
    # Формати:
    # - register_{id}
    # - register_{id}_date_{date_str}
    # - register_{id}_my_registrations
    
    parts = callback.data.split("_")
    session_id = int(parts[1])
    
    # Визначаємо контекст
    context = "schedule"  # за замовчуванням
    date_str = None
    
    if len(parts) > 2:
        if parts[2] == "date" and len(parts) > 3:
            context = "date"
            date_str = parts[3]
        elif parts[2] == "my" and len(parts) > 3 and parts[3] == "registrations":
            context = "my_registrations"
    
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
            
            # Показуємо оновлену інформацію про сесію зі збереженням контексту
            # Створюємо новий callback з правильним session_id і контекстом
            from aiogram.types import CallbackQuery as CQ
            
            # Формуємо callback_data з контекстом
            if context == "date" and date_str:
                callback_data = f"view_session_{session_id}_date_{date_str}"
            elif context == "my_registrations":
                callback_data = f"view_session_{session_id}_my_registrations"
            else:
                callback_data = f"view_session_{session_id}"
            
            new_callback = CQ(
                id=callback.id,
                from_user=callback.from_user,
                message=callback.message,
                chat_instance=callback.chat_instance,
                data=callback_data,
                inline_message_id=None
            )
            # Прив'язуємо bot до callback
            new_callback._bot = callback.bot
            await view_session_details(new_callback, skip_answer=True)
        else:
            await callback.answer(message, show_alert=True)


@router.callback_query(F.data.startswith("unregister_"))
async def unregister_from_game(callback: CallbackQuery):
    """Скасувати реєстрацію на гру"""
    # Парсимо callback_data
    # Формати:
    # - unregister_{id}
    # - unregister_{id}_date_{date_str}
    # - unregister_{id}_my_registrations
    
    parts = callback.data.split("_")
    session_id = int(parts[1])
    
    # Визначаємо контекст
    context = "schedule"  # за замовчуванням
    date_str = None
    
    if len(parts) > 2:
        if parts[2] == "date" and len(parts) > 3:
            context = "date"
            date_str = parts[3]
        elif parts[2] == "my" and len(parts) > 3 and parts[3] == "registrations":
            context = "my_registrations"
    
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
            
            # Показуємо оновлену інформацію про сесію зі збереженням контексту
            from aiogram.types import CallbackQuery as CQ
            
            # Формуємо callback_data з контекстом
            if context == "date" and date_str:
                callback_data = f"view_session_{session_id}_date_{date_str}"
            elif context == "my_registrations":
                callback_data = f"view_session_{session_id}_my_registrations"
            else:
                callback_data = f"view_session_{session_id}"
            
            new_callback = CQ(
                id=callback.id,
                from_user=callback.from_user,
                message=callback.message,
                chat_instance=callback.chat_instance,
                data=callback_data,
                inline_message_id=None
            )
            # Прив'язуємо bot до callback
            new_callback._bot = callback.bot
            await view_session_details(new_callback, skip_answer=True)
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
                # Перевіряємо, чи гра активна
                game = await get_game(db_session, game_session.game_id)
                if game and game.is_active:
                    future_registrations.append(reg)
        
        if future_registrations:
            # Створюємо клавіатуру тільки для майбутніх сесій з контекстом
            keyboard = []
            for reg in future_registrations:
                keyboard.append([{
                    "text": f"Переглянути сесію #{reg.session_id}",
                    "callback_data": f"view_session_{reg.session_id}_my_registrations"
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
    # Парсимо callback_data
    # Формати:
    # - players_list_{id}
    # - players_list_{id}_date_{date_str}
    # - players_list_{id}_my_registrations
    
    parts = callback.data.split("_")
    session_id = int(parts[2])  # players_list_{id}...
    
    # Визначаємо контекст
    context = "schedule"  # за замовчуванням
    date_str = None
    
    if len(parts) > 3:
        if parts[3] == "date" and len(parts) > 4:
            context = "date"
            date_str = parts[4]
        elif parts[3] == "my" and len(parts) > 4 and parts[4] == "registrations":
            context = "my_registrations"
    
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
        if not game or not game.is_active:
            await callback.answer("Гру не знайдено або вона була скасована", show_alert=True)
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
        
        # Кнопка назад зі збереженням контексту
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        
        # Формуємо callback_data з контекстом
        if context == "date" and date_str:
            callback_data = f"view_session_{session_id}_date_{date_str}"
        elif context == "my_registrations":
            callback_data = f"view_session_{session_id}_my_registrations"
        else:
            callback_data = f"view_session_{session_id}"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data=callback_data)]
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
    import logging
    logger = logging.getLogger(__name__)
    
    try:
        # Отримуємо розклад
        async for session in get_session():
            # Отримуємо майбутні сесії
            sessions = await ScheduleService.get_upcoming_schedule(session, days=7)
            
            if not sessions:
                text = "📅 На найближчі 7 днів немає запланованих ігор.\n\nСлідкуйте за оновленнями!"
                keyboard = []
            else:
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
            
            # Перевіряємо, чи повідомлення містить фото
            has_photo = callback.message.photo is not None
            
            # Спробуємо редагувати повідомлення
            try:
                if has_photo:
                    # Якщо є фото, оновлюємо caption
                    await callback.message.edit_caption(
                        caption=text,
                        reply_markup=kb,
                        parse_mode="HTML"
                    )
                else:
                    # Якщо немає фото, редагуємо текст
                    await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception as edit_error:
                # Якщо не вдалося редагувати, спробуємо видалити і відправити нове
                try:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
                except Exception as delete_error:
                    logger.error(f"back_to_schedule: Помилка при роботі з повідомленням: {delete_error}")
                    await callback.answer("Помилка при завантаженні розкладу. Спробуйте ще раз.", show_alert=True)
            
            await callback.answer()
            break
            
    except Exception as e:
        logger.error(f"back_to_schedule: Критична помилка: {e}")
        await callback.answer("Помилка при завантаженні розкладу. Спробуйте ще раз.", show_alert=True)


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


@router.callback_query(F.data == "back_to_my_registrations")
async def back_to_my_registrations(callback: CallbackQuery):
    """Повернутися до моїх записів"""
    # Видаляємо поточне повідомлення і викликаємо показ моїх записів
    await callback.message.delete()
    
    # Створюємо об'єкт Message для виклику show_my_registrations
    from aiogram.types import Message as Msg
    new_message = Msg(
        message_id=callback.message.message_id,
        date=callback.message.date,
        chat=callback.message.chat,
        from_user=callback.from_user,
        text="🎮 Мої записи"
    )
    # Прив'язуємо bot до message
    new_message._bot = callback.bot
    
    await show_my_registrations(new_message)
    await callback.answer()
