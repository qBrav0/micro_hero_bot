from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from datetime import date
import logging

from database import get_session, get_user_by_telegram_id
from services import RegistrationService, NotificationService, CombinedScheduleService
from keyboards import get_game_actions_keyboard
from utils.helpers import format_date, format_time, format_time_safe
from database.crud import get_game, get_registrations

router = Router()
logger = logging.getLogger(__name__)


@router.message(F.text == "📅 Розклад ігротеки")
async def show_schedule(message: Message):
    """Показати розклад ігор та подій з пагінацією"""
    async for session in get_session():
        # Отримуємо об'єднаний розклад (ігри + події)
        combined_schedule = await CombinedScheduleService.get_all_upcoming_schedule(session)
        
        if not combined_schedule:
            await message.answer(
                "📅 На майбутні дні немає запланованих ігор та подій.\n\n"
                "Слідкуйте за оновленнями!"
            )
            return
        
        
        text = f"📅 <b>Розклад ігротеки:</b>\n\n"
        text += "🎮 <b>Ігри</b> - ігрові сесії з настільних ігор\n"
        text += "🎪 <b>Події</b> - турніри, майстер-класи, спеціальні заходи\n\n"
        text += "Оберіть дату для перегляду:"
        
        # Використовуємо нову клавіатуру з пагінацією
        from keyboards.inline_keyboards import get_schedule_paginated_keyboard
        kb = get_schedule_paginated_keyboard(combined_schedule, page=0)
        
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("schedule_date_"))
async def show_date_sessions(callback: CallbackQuery):
    """Показати ігри та події на обрану дату"""
    await callback.answer()
    
    date_str = callback.data.split("_")[-1]
    selected_date = date.fromisoformat(date_str)
    
    async for session in get_session():
        # Отримуємо об'єднаний розклад на цю дату
        items = await CombinedScheduleService.get_schedule_for_date(session, selected_date)
        
        if not items:
            await callback.message.edit_text(
                f"📅 <b>{format_date(selected_date)}</b>\n\n"
                "На цю дату немає запланованих ігор та подій",
                parse_mode="HTML"
            )
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
        
        # Створюємо клавіатуру з іграми та подіями
        keyboard = []
        active_items_found = False
        
        # Сортуємо елементи по часу
        sorted_items = sorted(items, key=lambda x: x.start_time)
        
        for item in sorted_items:
            if CombinedScheduleService.is_game_session(item):
                # Це ігрова сесія
                game = await get_game(session, item.game_id)
                if not game or not game.is_active:
                    continue
                
                active_items_found = True
                registrations = await get_registrations(session, item.id, active_only=True)
                players_count = len(registrations)
                
                # Додаємо іконку типу оплати
                payment_icon = {
                    "included": "✅",
                    "free": "🎁",
                    "donate": "💝"
                }
                
                game_info = f"{payment_icon.get(item.payment_type, '✅')} 🎮 {game.name} • {format_time(item.start_time)}"
                game_info += f" • {players_count}/{game.max_players}"
                
                # Додаємо контекст дати в callback
                keyboard.append([{
                    "text": game_info,
                    "callback_data": f"view_session_{item.id}_date_{date_str}"
                }])
            
            elif CombinedScheduleService.is_event(item):
                # Це подія
                from database.crud import get_event_registrations
                registrations = await get_event_registrations(session, item.id, active_only=True)
                participants_count = len(registrations)
                
                active_items_found = True
                
                # Додаємо іконку типу оплати
                payment_icon = {
                    "included": "✅",
                    "free": "🎁",
                    "donate": "💝"
                }
                
                event_info = f"{payment_icon.get(item.payment_type, '✅')} 🎪 {item.title} • {format_time(item.start_time)}"
                event_info += f" • {participants_count}/{item.max_participants}"
                
                # Додаємо контекст дати в callback
                keyboard.append([{
                    "text": event_info,
                    "callback_data": f"view_event_{item.id}_date_{date_str}"
                }])
        
        # Якщо не знайшли активних елементів, показуємо відповідне повідомлення
        if not active_items_found:
            text += "На цю дату немає запланованих ігор та подій"
            keyboard.append([{"text": "🔙 Назад до дат", "callback_data": "back_to_schedule"}])
            
            from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
            kb = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
                for row in keyboard for btn in row
            ])
            
            # Перевіряємо, чи повідомлення містить фото
            has_photo = callback.message.photo is not None
            
            if has_photo:
                # Якщо є фото, завжди видаляємо і відправляємо нове текстове повідомлення
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
            # Якщо є фото, завжди видаляємо і відправляємо нове текстове повідомлення
            # (бо список ігор дня не повинен містити зображень)
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


@router.callback_query(F.data.startswith("view_event_"))
async def view_event_details(callback: CallbackQuery):
    """Показати деталі події"""
    # Парсимо callback_data: view_event_{event_id} або view_event_{event_id}_date_{date_str} або view_event_{event_id}_my_registrations
    parts = callback.data.split("_")
    event_id = int(parts[2])
    
    # Визначаємо контекст
    context = "schedule"  # за замовчуванням
    date_str = None
    
    if len(parts) > 3:
        if parts[3] == "date" and len(parts) > 4:
            context = "date"
            date_str = parts[4]
        elif parts[3] == "my" and len(parts) > 4 and parts[4] == "registrations":
            context = "my_registrations"
    
    user_telegram_id = callback.from_user.id
    
    async for db_session in get_session():
        from database import get_user_by_telegram_id
        from services import EventService
        from database.crud import check_user_registered_for_event, get_event_registrations
        
        # Отримуємо користувача
        user = await get_user_by_telegram_id(db_session, user_telegram_id)
        if not user:
            await callback.answer("❌ Помилка: користувача не знайдено", show_alert=True)
            return
        
        # Отримуємо подію
        event = await EventService.get_event_by_id(db_session, event_id)
        if not event:
            await callback.answer("❌ Подію не знайдено", show_alert=True)
            return
        
        # Відповідаємо на callback щоб прибрати "завантажувальний" стан
        await callback.answer()
        
        # Отримуємо реєстрації
        registrations = await get_event_registrations(db_session, event_id, active_only=True)
        participants_count = len(registrations)
        
        # Перевіряємо, чи зареєстрований користувач
        is_registered = await check_user_registered_for_event(db_session, user.id, event_id)
        
        # Формуємо текст
        text = f"🎪 <b>{event.title}</b>\n\n"
        text += f"📅 <b>Дата:</b> {format_date(event.date)}\n"
        text += f"⏰ <b>Час:</b> {format_time(event.start_time)} - {format_time(event.end_time)}\n"
        text += f"👥 <b>Учасників:</b> {participants_count}/{event.max_participants}\n\n"
        
        # Додаємо тип оплати
        payment_type_text = {
            "included": "✅ Входить в оплату за вхід",
            "free": "🎁 Безкоштовна",
            "donate": "💝 Free donate"
        }
        text += f"💳 <b>Оплата:</b> {payment_type_text.get(event.payment_type, 'Входить в оплату')}\n\n"
        
        # Додаємо опис
        text += f"📝 <b>Опис:</b>\n{event.description}\n\n"
        
        # Додаємо статус реєстрації
        if is_registered:
            text += "✅ <b>Ви зареєстровані на цю подію</b>"
        else:
            if participants_count >= event.max_participants:
                text += "❌ <b>Місця закінчилися</b>"
            else:
                text += "📝 <b>Ви можете зареєструватися на цю подію</b>"
        
        # Створюємо клавіатуру з контекстом
        from keyboards import get_event_actions_keyboard
        keyboard = get_event_actions_keyboard(event_id, is_registered=is_registered, context=context, date_str=date_str)
        
        # Перевіряємо чи є фото події
        has_image = event.image_file_id
        
        if has_image:
            # Перевіряємо, чи поточне повідомлення містить фото
            has_photo = callback.message.photo is not None
            
            if has_photo:
                # Якщо вже є фото, оновлюємо caption
                try:
                    await callback.message.edit_caption(
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                except Exception:
                    # Якщо не вдалося оновити caption, видаляємо і відправляємо нове
                    try:
                        await callback.message.delete()
                        await callback.message.answer_photo(
                            photo=event.image_file_id,
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
                    except Exception as e2:
                        # Якщо file_id невалідний, відправляємо тільки текст
                        logger.warning(f"Невалідний image_file_id для події {event_id}. Відправка без фото. Помилка: {e2}")
                        try:
                            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                        except Exception:
                            pass
            else:
                # Якщо немає фото, видаляємо поточне повідомлення і відправляємо нове фото з підписом
                try:
                    await callback.message.delete()
                    await callback.message.answer_photo(
                        photo=event.image_file_id,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    # Якщо не вдалося відправити фото (невалідний file_id), відправляємо тільки текст
                    # Повідомлення вже видалене, тому відправляємо нове
                    logger.warning(f"Невалідний image_file_id для події {event_id}. Відправка без фото. Помилка: {e}")
                    try:
                        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                    except Exception:
                        pass
        else:
            # Якщо немає фото події, перевіряємо чи поточне повідомлення містить фото
            has_photo = callback.message.photo is not None
            
            if has_photo:
                # Якщо є фото, але події немає фото, видаляємо і відправляємо текст
                try:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                except Exception:
                    pass
            else:
                # Відправляємо тільки текст
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")




@router.callback_query(F.data.startswith("schedule_page_"))
async def show_schedule_page(callback: CallbackQuery):
    """Показати сторінку розкладу"""
    page = int(callback.data.split("_")[-1])
    
    async for session in get_session():
        # Отримуємо об'єднаний розклад (ігри + події)
        combined_schedule = await CombinedScheduleService.get_all_upcoming_schedule(session)
        
        if not combined_schedule:
            await callback.answer("Немає запланованих ігор та подій", show_alert=True)
            return
        
        
        text = f"📅 <b>Розклад ігротеки:</b>\n\n"
        text += "🎮 <b>Ігри</b> - ігрові сесії з настільних ігор\n"
        text += "🎪 <b>Події</b> - турніри, майстер-класи, спеціальні заходи\n\n"
        text += "Оберіть дату для перегляду:"
        
        # Використовуємо нову клавіатуру з пагінацією
        from keyboards.inline_keyboards import get_schedule_paginated_keyboard
        kb = get_schedule_paginated_keyboard(combined_schedule, page=page)
        
        # Перевіряємо, чи повідомлення містить фото
        has_photo = callback.message.photo is not None
        
        if has_photo:
            # Якщо є фото, завжди видаляємо і відправляємо нове текстове повідомлення
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
        
        # Перевіряємо чи є зображення (Telegram file_id або локальний файл)
        has_image = game.image_file_id or (game.image_path and __import__('os').path.exists(game.image_path))
        
        # Відправляємо з фото якщо воно є
        if has_image and not has_photo:
            try:
                await callback.message.delete()
                
                # Використовуємо file_id якщо є, інакше локальний файл
                if game.image_file_id:
                    await callback.message.answer_photo(
                        photo=game.image_file_id,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                elif game.image_path:
                    from aiogram.types import FSInputFile
                    import os
                    if os.path.exists(game.image_path):
                        photo = FSInputFile(game.image_path)
                        await callback.message.answer_photo(
                            photo=photo,
                            caption=text,
                            reply_markup=keyboard,
                            parse_mode="HTML"
                        )
            except Exception as e:
                # Якщо не вдалося відправити фото (невалідний file_id), відправляємо тільки текст
                # Повідомлення вже видалене, тому відправляємо нове
                logger.warning(f"Невалідний image_file_id для гри {game.name} (session {session_id}). Відправка без фото. Помилка: {e}")
                try:
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                except Exception:
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
    """Показати записи користувача на ігрові сесії та події"""
    user_id = message.from_user.id
    
    async for db_session in get_session():
        # Отримуємо користувача
        user = await get_user_by_telegram_id(db_session, user_id)
        if not user:
            await message.answer("Помилка: користувача не знайдено")
            return
        
        # Отримуємо реєстрації на ігрові сесії
        game_registrations = await RegistrationService.get_user_active_registrations(
            db_session, user.id
        )
        
        # Отримуємо реєстрації на події
        from services import EventService
        event_registrations = await EventService.get_user_registrations(db_session, user.id)
        
        # Фільтруємо тільки майбутні записи
        from sqlmodel import select
        from database.models import GameSession, Event
        from datetime import date
        
        today = date.today()
        
        # Обробляємо ігрові сесії
        future_game_items = []
        for reg in game_registrations:
            result = await db_session.execute(
                select(GameSession).where(GameSession.id == reg.session_id)
            )
            game_session = result.scalar_one_or_none()
            
            if game_session and game_session.date >= today:
                game = await get_game(db_session, game_session.game_id)
                if game and game.is_active:
                    future_game_items.append({
                        'type': 'game',
                        'date': game_session.date,
                        'time': game_session.start_time,
                        'session_id': game_session.id,
                        'name': game.name,
                        'registration': reg
                    })
        
        # Обробляємо події
        future_event_items = []
        for reg in event_registrations:
            result = await db_session.execute(
                select(Event).where(Event.id == reg.event_id)
            )
            event = result.scalar_one_or_none()
            
            if event and event.date >= today:
                future_event_items.append({
                    'type': 'event',
                    'date': event.date,
                    'time': event.start_time,
                    'event_id': event.id,
                    'name': event.title,
                    'registration': reg
                })
        
        # Об'єднуємо та сортуємо за датою і часом
        all_items = future_game_items + future_event_items
        all_items.sort(key=lambda x: (x['date'], x['time']))
        
        # Формуємо текст
        if not all_items:
            text = "🎮 <b>Мої записи</b>\n\n"
            text += "У вас немає активних записів на ігри та події.\n\n"
            text += "📅 Перегляньте розклад і запишіться на цікаві вам заходи!"
            await message.answer(text, parse_mode="HTML")
            return
        
        text = "🎮 <b>Мої записи</b>\n\n"
        text += "Ваші майбутні ігри та події:\n\n"
        
        # Групуємо по датах для відображення
        current_date = None
        for item in all_items:
            if current_date != item['date']:
                current_date = item['date']
                text += f"\n📅 <b>{format_date(current_date)}</b>\n"
            
            if item['type'] == 'game':
                text += f"🎮 {item['name']} • {format_time(item['time'])}\n"
            else:  # event
                text += f"🎪 {item['name']} • {format_time(item['time'])}\n"
        
        # Створюємо клавіатуру
        keyboard = []
        for item in all_items:
            if item['type'] == 'game':
                button_text = f"🎮 {item['name']}"
                callback_data = f"view_session_{item['session_id']}_my_registrations"
            else:  # event
                button_text = f"🎪 {item['name']}"
                callback_data = f"view_event_{item['event_id']}_my_registrations"
            
            keyboard.append([{
                "text": button_text,
                "callback_data": callback_data
            }])
        
        from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
        kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=btn["text"], callback_data=btn["callback_data"])]
            for row in keyboard for btn in row
        ])
        
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


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
            # Отримуємо об'єднаний розклад (ігри + події)
            combined_schedule = await CombinedScheduleService.get_all_upcoming_schedule(session)
            
            if not combined_schedule:
                text = "📅 На майбутні дні немає запланованих ігор та подій.\n\nСлідкуйте за оновленнями!"
                kb = None
            else:
                
                text = f"📅 <b>Розклад ігротеки:</b>\n\n"
                text += "🎮 <b>Ігри</b> - ігрові сесії з настільних ігор\n"
                text += "🎪 <b>Події</b> - турніри, майстер-класи, спеціальні заходи\n\n"
                text += "Оберіть дату для перегляду:"
                
                # Використовуємо нову клавіатуру з пагінацією
                from keyboards.inline_keyboards import get_schedule_paginated_keyboard
                kb = get_schedule_paginated_keyboard(combined_schedule, page=0)
            
            # Перевіряємо, чи повідомлення містить фото
            has_photo = callback.message.photo is not None
            
            # Спробуємо редагувати повідомлення
            try:
                if has_photo:
                    # Якщо є фото, завжди видаляємо і відправляємо нове текстове повідомлення
                    # (бо розклад не повинен містити зображень)
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
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


# ===== ОБРОБНИКИ ПОДІЙ =====

@router.callback_query(F.data.startswith("event_register_"))
async def register_for_event_from_schedule(callback: CallbackQuery):
    """Зареєструватися на подію"""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    # Контекст: event_register_{id} | event_register_{id}_date_{date_str} | event_register_{id}_my_registrations
    context = "schedule"
    date_str = None
    if len(parts) > 3:
        if parts[3] == "date" and len(parts) > 4:
            context = "date"
            date_str = parts[4]
        elif parts[3] == "my" and len(parts) > 4 and parts[4] == "registrations":
            context = "my_registrations"
    user_telegram_id = callback.from_user.id
    
    async for session in get_session():
        from database import get_user_by_telegram_id
        from services import EventService
        from database.crud import check_user_registered_for_event
        
        # Отримуємо користувача
        user = await get_user_by_telegram_id(session, user_telegram_id)
        if not user:
            await callback.answer("❌ Помилка: користувача не знайдено", show_alert=True)
            return
        
        # Перевіряємо чи вже зареєстрований
        if await check_user_registered_for_event(session, user.id, event_id):
            await callback.answer("⚠️ Ви вже зареєстровані на цю подію", show_alert=True)
            return
        
        # Реєструємо користувача
        success = await EventService.register_user_for_event(session, user.id, event_id)
        
        if success:
            event = await EventService.get_event_by_id(session, event_id)
            await callback.answer(f"✅ Ви успішно зареєстровані на подію '{event.title}'!")
            
            # Відправляємо сповіщення адміністраторам
            bot = callback.bot
            from services import NotificationService
            await NotificationService.notify_admins_new_event_registration(
                bot, session, event, user
            )
            
            # Оновлюємо відображення події з новими кнопками, зберігаючи контекст
            from aiogram.types import CallbackQuery as CQ
            if context == "date" and date_str:
                new_data = f"view_event_{event_id}_date_{date_str}"
            elif context == "my_registrations":
                new_data = f"view_event_{event_id}_my_registrations"
            else:
                new_data = f"view_event_{event_id}"
            new_callback = CQ(
                id=callback.id,
                from_user=callback.from_user,
                message=callback.message,
                chat_instance=callback.chat_instance,
                data=new_data,
                inline_message_id=None
            )
            new_callback._bot = callback.bot
            await view_event_details(new_callback)
        else:
            await callback.answer("❌ Не вдалося зареєструватися. Можливо, місця закінчилися.", show_alert=True)


@router.callback_query(F.data.startswith("event_cancel_"))
async def cancel_event_registration_from_schedule(callback: CallbackQuery):
    """Скасувати реєстрацію на подію"""
    parts = callback.data.split("_")
    event_id = int(parts[2])
    # Контекст: event_cancel_{id} | event_cancel_{id}_date_{date_str} | event_cancel_{id}_my_registrations
    context = "schedule"
    date_str = None
    if len(parts) > 3:
        if parts[3] == "date" and len(parts) > 4:
            context = "date"
            date_str = parts[4]
        elif parts[3] == "my" and len(parts) > 4 and parts[4] == "registrations":
            context = "my_registrations"
    user_telegram_id = callback.from_user.id
    
    async for session in get_session():
        from database import get_user_by_telegram_id
        from services import EventService
        
        # Отримуємо користувача
        user = await get_user_by_telegram_id(session, user_telegram_id)
        if not user:
            await callback.answer("❌ Помилка: користувача не знайдено", show_alert=True)
            return
        
        # Отримуємо подію перед скасуванням для сповіщення
        event = await EventService.get_event_by_id(session, event_id)
        
        # Скасовуємо реєстрацію
        success = await EventService.cancel_user_registration(session, user.id, event_id)
        
        if success:
            await callback.answer(f"❌ Реєстрацію на подію '{event.title}' скасовано")
            
            # Відправляємо сповіщення адміністраторам
            bot = callback.bot
            from services import NotificationService
            await NotificationService.notify_admins_event_cancellation(
                bot, session, event, user
            )
            
            # Оновлюємо відображення події з новими кнопками, зберігаючи контекст
            from aiogram.types import CallbackQuery as CQ
            if context == "date" and date_str:
                new_data = f"view_event_{event_id}_date_{date_str}"
            elif context == "my_registrations":
                new_data = f"view_event_{event_id}_my_registrations"
            else:
                new_data = f"view_event_{event_id}"
            new_callback = CQ(
                id=callback.id,
                from_user=callback.from_user,
                message=callback.message,
                chat_instance=callback.chat_instance,
                data=new_data,
                inline_message_id=None
            )
            new_callback._bot = callback.bot
            await view_event_details(new_callback)
        else:
            await callback.answer("❌ Не вдалося скасувати реєстрацію", show_alert=True)


@router.callback_query(F.data.startswith("event_participants_list_"))
async def show_event_participants_list_from_schedule(callback: CallbackQuery):
    """Показати список учасників події з розкладу"""
    parts = callback.data.split("_")
    event_id = int(parts[3])
    # Контекст: event_participants_list_{id} | ..._date_{date_str} | ..._my_registrations
    context = "schedule"
    date_str = None
    if len(parts) > 4:
        if parts[4] == "date" and len(parts) > 5:
            context = "date"
            date_str = parts[5]
        elif parts[4] == "my" and len(parts) > 5 and parts[5] == "registrations":
            context = "my_registrations"
    
    async for db_session in get_session():
        # Отримуємо подію
        from sqlmodel import select
        from database.models import Event, User
        
        result = await db_session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not event:
            await callback.answer("Подію не знайдено", show_alert=True)
            return
        
        # Отримуємо реєстрації
        from database.crud import get_event_registrations
        registrations = await get_event_registrations(db_session, event_id, active_only=True)
        
        text = f"👥 <b>Список учасників</b>\n\n"
        text += f"🎪 Подія: <b>{event.title}</b>\n"
        text += f"📅 Дата: {format_date(event.date)}\n"
        text += f"⏰ Час: {format_time(event.start_time)} - {format_time(event.end_time)}\n\n"
        
        if not registrations:
            text += "Поки що ніхто не зареєстрований на цю подію."
            # Кнопка назад зі збереженням контексту
            if context == "date" and date_str:
                back_cb = f"view_event_{event_id}_date_{date_str}"
            elif context == "my_registrations":
                back_cb = f"view_event_{event_id}_my_registrations"
            else:
                back_cb = f"view_event_{event_id}"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)]])
        else:
            text += f"<b>Зареєстровано: {len(registrations)}/{event.max_participants}</b>\n\n"
            
            # Отримуємо інформацію про кожного учасника
            for i, reg in enumerate(registrations, 1):
                result = await db_session.execute(
                    select(User).where(User.id == reg.user_id)
                )
                participant = result.scalar_one_or_none()
                
                if participant:
                    participant_name = participant.first_name
                    if participant.last_name:
                        participant_name += f" {participant.last_name}"
                    
                    if participant.username:
                        text += f"{i}. @{participant.username} ({participant_name})\n"
                    else:
                        text += f"{i}. {participant_name}\n"
            
            if context == "date" and date_str:
                back_cb = f"view_event_{event_id}_date_{date_str}"
            elif context == "my_registrations":
                back_cb = f"view_event_{event_id}_my_registrations"
            else:
                back_cb = f"view_event_{event_id}"
            keyboard = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="🔙 Назад", callback_data=back_cb)]])
        
        # Перевіряємо чи є фото в повідомленні
        has_photo = callback.message.photo is not None
        
        if has_photo:
            # Якщо є фото, видаляємо і відправляємо нове текстове повідомлення
            try:
                await callback.message.delete()
                await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                pass
        else:
            # Якщо немає фото, редагуємо текст
            try:
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                # Якщо не вдалося редагувати, видаляємо і відправляємо нове
                try:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                except Exception:
                    pass
        
        await callback.answer()


@router.callback_query(F.data == "back_to_events")
async def back_to_events(callback: CallbackQuery):
    """Повернутися до розкладу ігротеки"""
    async for session in get_session():
        # Отримуємо об'єднаний розклад (ігри + події)
        combined_schedule = await CombinedScheduleService.get_all_upcoming_schedule(session)
        
        if not combined_schedule:
            await callback.answer("Немає запланованих ігор та подій", show_alert=True)
            return
        
        
        text = f"📅 <b>Розклад ігротеки:</b>\n\n"
        text += "🎮 <b>Ігри</b> - ігрові сесії з настільних ігор\n"
        text += "🎪 <b>Події</b> - турніри, майстер-класи, спеціальні заходи\n\n"
        text += "Оберіть дату для перегляду:"
        
        # Використовуємо нову клавіатуру з пагінацією
        from keyboards.inline_keyboards import get_schedule_paginated_keyboard
        kb = get_schedule_paginated_keyboard(combined_schedule, page=0)
        
        # Перевіряємо, чи поточне повідомлення містить фото
        has_photo = callback.message.photo is not None
        
        if has_photo:
            # Якщо є фото, видаляємо і відправляємо нове текстове повідомлення
            try:
                await callback.message.delete()
                await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                pass
        else:
            # Якщо немає фото, редагуємо текст
            try:
                await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
            except Exception:
                # Якщо не вдалося редагувати текст, спробуємо видалити і відправити нове
                try:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=kb, parse_mode="HTML")
                except Exception:
                    pass
        
        await callback.answer()




