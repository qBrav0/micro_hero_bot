from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import date
import os
import logging

from database import get_session
from services import EventService
from keyboards import (
    get_admin_events_menu, get_events_list_keyboard, get_event_actions_keyboard,
    get_event_edit_keyboard, get_date_selection_keyboard, get_confirmation_keyboard
)
from utils.decorators import admin_only
from utils.validators import validate_time, validate_date, validate_players_count, normalize_time
from utils.helpers import format_date, format_time
from database.crud import get_event, get_event_registrations

router = Router()
logger = logging.getLogger(__name__)


# FSM стани для створення події
class CreateEventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_min_participants = State()
    waiting_for_max_participants = State()
    waiting_for_payment_type = State()
    waiting_for_image = State()


# FSM стани для редагування події
class EditEventStates(StatesGroup):
    waiting_for_title = State()
    waiting_for_description = State()
    waiting_for_date = State()
    waiting_for_start_time = State()
    waiting_for_end_time = State()
    waiting_for_min_participants = State()
    waiting_for_max_participants = State()
    waiting_for_payment_type = State()
    waiting_for_image = State()


class KickPlayerStates(StatesGroup):
    waiting_for_reason = State()
    waiting_for_confirmation = State()


# ===== АДМІНІСТРАТИВНІ ОБРОБНИКИ =====

@router.message(F.text == "🎪 Управління подіями")
@admin_only
async def show_events_management(message: Message, state: FSMContext):
    """Показати меню управління подіями"""
    # Перевіряємо чи не в процесі створення щось
    current_state = await state.get_state()
    if current_state is None:
        # Тільки очищаємо якщо не в FSM процесі
        await state.clear()
    
    text = "🎪 <b>Управління подіями</b>\n\n"
    text += "Оберіть дію:"
    
    await message.answer(
        text,
        reply_markup=get_admin_events_menu(),
        parse_mode="HTML"
    )


@router.message(F.text == "➕ Створити подію")
@admin_only
async def start_create_event(message: Message, state: FSMContext):
    """Почати створення події"""
    await state.set_state(CreateEventStates.waiting_for_title)
    await message.answer(
        "🎪 <b>Створення нової події</b>\n\n"
        "Введіть назву події:",
        parse_mode="HTML"
    )


@router.message(CreateEventStates.waiting_for_title)
async def process_event_title(message: Message, state: FSMContext):
    """Обробка назви події"""
    await state.update_data(title=message.text)
    await state.set_state(CreateEventStates.waiting_for_description)
    await message.answer("📝 Введіть опис події:")


@router.message(CreateEventStates.waiting_for_description)
async def process_event_description(message: Message, state: FSMContext):
    """Обробка опису події"""
    await state.update_data(description=message.text)
    await state.set_state(CreateEventStates.waiting_for_date)
    
    text = "📅 <b>Оберіть дату проведення</b>\n\n"
    text += "Оберіть дату або введіть вручну (ДД.ММ.РРРР):"
    
    keyboard = get_date_selection_keyboard(prefix="select_event_date")
    
    await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("select_event_date_"))
@admin_only
async def process_event_date_selection(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору дати для події"""
    logger.info(f"🔍 [EVENT_DATE_SELECTION] Початок обробки вибору дати для події. callback_data: {callback.data}")
    logger.info(f"🔍 [EVENT_DATE_SELECTION] Користувач: {callback.from_user.username} (ID: {callback.from_user.id})")
    
    try:
        await callback.answer()
        logger.info(f"✅ [EVENT_DATE_SELECTION] callback.answer() виконано успішно")
    except Exception as e:
        logger.error(f"❌ [EVENT_DATE_SELECTION] Помилка при виклику callback.answer(): {e}", exc_info=True)
    
    date_str = callback.data.split("_")[-1]
    logger.info(f"🔍 [EVENT_DATE_SELECTION] Розпарсена дата: {date_str}")
    
    try:
        selected_date = date.fromisoformat(date_str)
        logger.info(f"✅ [EVENT_DATE_SELECTION] Дата перетворена успішно: {selected_date}")
    except Exception as e:
        logger.error(f"❌ [EVENT_DATE_SELECTION] Помилка при перетворенні дати: {e}", exc_info=True)
        await callback.message.answer("❌ Помилка при обробці дати")
        return
    
    # Перевіряємо в якому стані ми знаходимося
    current_state = await state.get_state()
    logger.info(f"🔍 [EVENT_DATE_SELECTION] Поточний state: {current_state}")
    
    if current_state == CreateEventStates.waiting_for_date.state:
        logger.info(f"✅ [EVENT_DATE_SELECTION] Це створення нової події")
        # Це створення нової події
        await state.update_data(date=selected_date)
        await state.set_state(CreateEventStates.waiting_for_start_time)
        await callback.message.edit_text(
            f"📅 Дата: <b>{selected_date.strftime('%d.%m.%Y')}</b>\n\n"
            f"⏰ Введіть час початку (ЧЧ:ХХ):",
            parse_mode="HTML"
        )
    elif current_state == EditEventStates.waiting_for_date.state:
        # Це редагування існуючої події
        data = await state.get_data()
        event_id = data.get("edit_event_id")
        
        async for session in get_session():
            event = await EventService.get_event_by_id(session, event_id)
            if event:
                await EventService.update_event_info(session, event, date=selected_date)
                await callback.message.edit_text(
                    f"✅ Дату події змінено на: <b>{selected_date.strftime('%d.%m.%Y')}</b>",
                    parse_mode="HTML"
                )
        
        await state.clear()


@router.message(CreateEventStates.waiting_for_date)
async def process_custom_event_date(message: Message, state: FSMContext):
    """Обробка введеної дати для події"""
    valid, parsed_date, error_msg = validate_date(message.text)
    
    if not valid:
        await message.answer(error_msg)
        return
    
    await state.update_data(date=parsed_date)
    await state.set_state(CreateEventStates.waiting_for_start_time)
    await message.answer(
        f"📅 Дата: <b>{parsed_date.strftime('%d.%m.%Y')}</b>\n\n"
        f"⏰ Введіть час початку (ЧЧ:ХХ):"
    )


@router.message(CreateEventStates.waiting_for_start_time)
async def process_event_start_time(message: Message, state: FSMContext):
    """Обробка часу початку події"""
    valid, parsed_time, error_msg = validate_time(message.text)
    
    if not valid:
        await message.answer(error_msg)
        return
    
    normalized_time = normalize_time(message.text)
    await state.update_data(start_time=normalized_time)
    await state.set_state(CreateEventStates.waiting_for_end_time)
    await message.answer("⏰ Введіть час закінчення (ЧЧ:ХХ):")


@router.message(CreateEventStates.waiting_for_end_time)
async def process_event_end_time(message: Message, state: FSMContext):
    """Обробка часу закінчення події"""
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
    await state.set_state(CreateEventStates.waiting_for_min_participants)
    await message.answer("👥 Введіть мінімальну кількість учасників:")


@router.message(CreateEventStates.waiting_for_min_participants)
async def process_event_min_participants(message: Message, state: FSMContext):
    """Обробка мінімальної кількості учасників"""
    try:
        min_participants = int(message.text)
        if min_participants < 1:
            await message.answer("⚠️ Мінімальна кількість учасників повинна бути більше 0")
            return
        
        await state.update_data(min_participants=min_participants)
        await state.set_state(CreateEventStates.waiting_for_max_participants)
        await message.answer("👥 Введіть максимальну кількість учасників:")
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.message(CreateEventStates.waiting_for_max_participants)
async def process_event_max_participants(message: Message, state: FSMContext):
    """Обробка максимальної кількості учасників"""
    try:
        max_participants = int(message.text)
        data = await state.get_data()
        min_participants = data.get("min_participants", 1)
        
        # Валідація
        valid, error_msg = validate_players_count(min_participants, max_participants)
        if not valid:
            await message.answer(error_msg)
            return
        
        await state.update_data(max_participants=max_participants)
        await state.set_state(CreateEventStates.waiting_for_payment_type)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="✅ Входить в оплату за вхід", callback_data="event_payment_included")],
            [InlineKeyboardButton(text="🎁 Безкоштовна", callback_data="event_payment_free")],
            [InlineKeyboardButton(text="💝 Free donate", callback_data="event_payment_donate")]
        ])
        
        await message.answer(
            "💳 Оберіть тип оплати для цієї події:",
            reply_markup=keyboard
        )
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.callback_query(F.data.in_(["event_payment_included", "event_payment_free", "event_payment_donate"]))
@admin_only
async def process_event_payment_type(callback: CallbackQuery, state: FSMContext):
    """Обробка вибору типу оплати та перехід до додавання фото"""
    payment_types = {
        "event_payment_included": "included",
        "event_payment_free": "free",
        "event_payment_donate": "donate"
    }
    
    payment_type = payment_types[callback.data]
    await state.update_data(payment_type=payment_type)
    await state.set_state(CreateEventStates.waiting_for_image)
    
    await callback.message.edit_text(
        "📸 Надішліть зображення події або введіть /skip щоб пропустити:"
    )
    await callback.answer()


@router.message(CreateEventStates.waiting_for_image, F.photo)
async def process_event_image(message: Message, state: FSMContext):
    """Обробка зображення події"""
    import logging
    
    # Зберігаємо Telegram file_id
    photo = message.photo[-1]  # Беремо найбільше фото
    file_id = photo.file_id
    
    logging.info(f"✅ Збережено Telegram file_id для події: {file_id}")
    
    # Зберігаємо file_id в стан
    await state.update_data(image_file_id=file_id)
    await message.answer("✅ Зображення збережено!")
    
    await save_event(message, state)


@router.message(CreateEventStates.waiting_for_image, F.text == "/skip")
async def skip_event_image(message: Message, state: FSMContext):
    """Пропустити зображення"""
    await state.update_data(image_file_id=None)
    await save_event(message, state)


async def save_event(message: Message, state: FSMContext):
    """Зберегти подію в базу даних"""
    data = await state.get_data()
    user_telegram_id = message.from_user.id
    
    async for session in get_session():
        from database import get_user_by_telegram_id
        user = await get_user_by_telegram_id(session, user_telegram_id)
        
        if not user:
            await message.answer("❌ Помилка: користувача не знайдено")
            await state.clear()
            return
        
        # Створюємо подію
        event = await EventService.create_new_event(
            session=session,
            title=data["title"],
            description=data["description"],
            min_participants=data["min_participants"],
            max_participants=data["max_participants"],
            date=data["date"],
            start_time=data["start_time"],
            end_time=data["end_time"],
            payment_type=data["payment_type"],
            created_by=user.id,
            image_file_id=data.get("image_file_id")
        )
        
        payment_type_text = {
            "included": "✅ Входить в оплату за вхід",
            "free": "🎁 Безкоштовна",
            "donate": "💝 Free donate"
        }
        
        await message.answer(
            f"✅ Подію <b>{event.title}</b> успішно створено!\n\n"
            f"📅 Дата: {data['date'].strftime('%d.%m.%Y')}\n"
            f"⏰ Час: {data['start_time']} - {data['end_time']}\n"
            f"👥 Учасників: {data['min_participants']}-{data['max_participants']}\n"
            f"💳 Оплата: {payment_type_text.get(data['payment_type'], 'Входить в оплату')}",
            reply_markup=get_admin_events_menu(),
            parse_mode="HTML"
        )
    
    await state.clear()


@router.message(F.text == "📋 Список подій")
@admin_only
async def show_events_list(message: Message):
    """Показати список подій"""
    async for session in get_session():
        events = await EventService.get_all_active_events(session)
        
        if not events:
            await message.answer("📋 Список подій порожній")
            return
        
        text = "📋 <b>Список подій:</b>\n\n"
        
        for i, event in enumerate(events, 1):
            text += f"{i}. 🎪 <b>{event.title}</b>\n"
            text += f"   📅 {format_date(event.date)} | ⏰ {format_time(event.start_time)} - {format_time(event.end_time)}\n"
            text += f"   👥 {event.min_participants}-{event.max_participants} учасників\n\n"
        
        # Клавіатура для вибору події
        keyboard = get_events_list_keyboard(events, for_registration=False)
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "admin_events_list")
async def back_to_events_list(callback: CallbackQuery):
    """Повернутися до списку подій"""
    await show_events_list_page(callback, page=0)


@router.callback_query(F.data.startswith("events_page_"))
async def handle_events_pagination(callback: CallbackQuery, state: FSMContext):
    """Обробка пагінації списку подій"""
    parts = callback.data.split("_")
    page = int(parts[2])
    page_type = parts[3] if len(parts) > 3 else "admin"  # register або admin
    
    if page_type == "register":
        await show_events_registration_list_page(callback, state, page=page)
    else:
        await show_events_list_page(callback, page=page)


async def show_events_list_page(callback: CallbackQuery, page: int = 0):
    """Показати сторінку списку подій"""
    async for session in get_session():
        events = await EventService.get_all_active_events(session)
        
        if not events:
            await callback.message.edit_text("📋 Список подій порожній")
            await callback.answer()
            return
        
        # Обчислюємо які події показувати
        items_per_page = 7
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        total_pages = (len(events) + items_per_page - 1) // items_per_page
        
        text = f"📋 <b>Список подій</b> (Сторінка {page + 1}/{total_pages})\n\n"
        
        # Показуємо тільки події поточної сторінки
        page_events = events[start_idx:end_idx]
        for i, event in enumerate(page_events, start_idx + 1):
            text += f"{i}. 🎪 <b>{event.title}</b>\n"
            text += f"   📅 {format_date(event.date)} | ⏰ {format_time(event.start_time)} - {format_time(event.end_time)}\n"
            text += f"   👥 {event.min_participants}-{event.max_participants} учасників\n\n"
        
        keyboard = get_events_list_keyboard(events, for_registration=False, page=page)
        
        # Перевіряємо, чи повідомлення містить фото
        has_photo = callback.message.photo is not None
        
        if has_photo:
            # Якщо є фото, завжди видаляємо і відправляємо нове текстове повідомлення
            # (бо список подій не повинен містити зображень)
            try:
                await callback.message.delete()
                await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception:
                pass
        else:
            # Якщо немає фото, редагуємо текст
            try:
                await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            except Exception as e:
                # Якщо не вдалося редагувати текст, спробуємо видалити і відправити нове
                try:
                    await callback.message.delete()
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
                except Exception:
                    pass
        
        await callback.answer()


async def show_events_registration_list_page(callback: CallbackQuery, state: FSMContext, page: int = 0):
    """Показати сторінку списку подій для реєстрації"""
    async for session in get_session():
        events = await EventService.get_all_active_events(session)
        
        if not events:
            await callback.message.edit_text("❌ Немає доступних подій")
            await callback.answer()
            return
        
        # Обчислюємо які події показувати
        items_per_page = 7
        start_idx = page * items_per_page
        end_idx = start_idx + items_per_page
        total_pages = (len(events) + items_per_page - 1) // items_per_page
        
        text = f"🎪 <b>Оберіть подію зі списку</b> (Сторінка {page + 1}/{total_pages}):"
        
        keyboard = get_events_list_keyboard(events, for_registration=True, page=page)
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("admin_event_"))
async def show_event_edit_menu(callback: CallbackQuery):
    """Показати меню редагування події"""
    event_id = int(callback.data.split("_")[-1])
    
    async for session in get_session():
        event = await EventService.get_event_by_id(session, event_id)
        
        if not event:
            await callback.answer("❌ Подію не знайдено", show_alert=True)
            return
        
        text = EventService.format_event_info_for_list(event)
        text += "\n<b>Оберіть що хочете змінити:</b>"
        
        keyboard = get_event_edit_keyboard(event_id)
        
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
                    # Якщо не вдалося відправити фото, відправляємо тільки текст
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
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


@router.message(F.text == "📅 Переглянути розклад подій")
@admin_only
async def view_admin_events_schedule(message: Message):
    """Переглянути розклад подій (адмін) з можливістю видалення"""
    async for db_session in get_session():
        events = await EventService.get_upcoming_schedule(db_session, days=14)
        
        if not events:
            await message.answer("📅 На найближчі 14 днів немає запланованих подій.")
            return
        
        text = "🎪 <b>Розклад подій (Адмін)</b>\n\n"
        text += "Оберіть подію для управління:"
        
        # Створюємо клавіатуру з подіями
        keyboard = []
        
        for event in events:
            registrations = await get_event_registrations(db_session, event.id, active_only=True)
            participants_count = len(registrations)
            
            button_text = f"🎪 {event.title} | {format_date(event.date)} {format_time(event.start_time)} | {participants_count}/{event.max_participants}"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"admin_manage_event_{event.id}"
                )
            ])
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await message.answer(text, reply_markup=kb, parse_mode="HTML")


@router.callback_query(F.data.startswith("admin_manage_event_"))
async def admin_manage_event(callback: CallbackQuery):
    """Управління подією (адмін)"""
    event_id = int(callback.data.split("_")[-1])
    
    async for db_session in get_session():
        event = await EventService.get_event_by_id(db_session, event_id)
        
        if not event:
            await callback.answer("❌ Подію не знайдено", show_alert=True)
            return
        
        registrations = await get_event_registrations(db_session, event_id, active_only=True)
        
        text = f"🎪 <b>{event.title}</b>\n\n"
        text += f"📅 <b>Дата:</b> {format_date(event.date)}\n"
        text += f"⏰ <b>Час:</b> {format_time(event.start_time)} - {format_time(event.end_time)}\n"
        text += f"👥 <b>Учасників:</b> {len(registrations)}/{event.max_participants}\n\n"
        
        # Додаємо тип оплати
        payment_type_text = {
            "included": "✅ Входить в оплату за вхід",
            "free": "🎁 Безкоштовна",
            "donate": "💝 Free donate"
        }
        text += f"💳 <b>Оплата:</b> {payment_type_text.get(event.payment_type, 'Входить в оплату')}\n\n"
        
        # Додаємо опис
        text += f"📝 <b>Опис:</b>\n{event.description}\n\n"
        
        text += "<b>Що ви хочете зробити?</b>"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="👥 Список учасників",
                    callback_data=f"admin_participants_list_{event_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🗑️ Видалити подію",
                    callback_data=f"admin_delete_event_{event_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔙 Назад до розкладу",
                    callback_data="admin_back_events_schedule"
                )
            ]
        ])
        
        # Перевіряємо чи є зображення події
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
                    except Exception:
                        # Якщо не вдалося відправити фото, відправляємо текст
                        await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            else:
                # Якщо немає фото, відправляємо фото з caption
                try:
                    await callback.message.delete()
                    await callback.message.answer_photo(
                        photo=event.image_file_id,
                        caption=text,
                        reply_markup=keyboard,
                        parse_mode="HTML"
                    )
                except Exception:
                    # Якщо не вдалося відправити фото, відправляємо текст
                    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            # Якщо немає зображення, просто редагуємо текст
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


@router.callback_query(F.data.startswith("admin_participants_list_"))
async def admin_show_participants_list(callback: CallbackQuery):
    """Показати список учасників події для адміна з можливістю кіку"""
    event_id = int(callback.data.split("_")[-1])
    
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
        registrations = await get_event_registrations(db_session, event_id, active_only=True)
        
        text = f"👥 <b>Список учасників (Адмін)</b>\n\n"
        text += f"🎪 Подія: <b>{event.title}</b>\n"
        text += f"📅 Дата: {format_date(event.date)}\n"
        text += f"⏰ Час: {format_time(event.start_time)} - {format_time(event.end_time)}\n\n"
        
        if not registrations:
            text += "Поки що ніхто не зареєстрований на цю подію."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin_manage_event_{event_id}")]
            ])
        else:
            text += f"<b>Зареєстровано: {len(registrations)}/{event.max_participants}</b>\n\n"
            
            # Отримуємо інформацію про кожного учасника
            keyboard_buttons = []
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
                    
                    # Кнопка кіку для кожного учасника
                    keyboard_buttons.append([
                        InlineKeyboardButton(
                            text=f"🚫 Кікнути {participant_name}",
                            callback_data=f"admin_kick_participant_{event_id}_{reg.user_id}"
                        )
                    ])
            
            # Додаємо кнопку назад
            keyboard_buttons.append([
                InlineKeyboardButton(text="🔙 Назад", callback_data=f"admin_manage_event_{event_id}")
            ])
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=keyboard_buttons)
        
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


@router.callback_query(F.data.startswith("admin_kick_participant_"))
async def admin_kick_participant_start(callback: CallbackQuery, state: FSMContext):
    """Почати процес кіку учасника з події"""
    parts = callback.data.split("_")
    event_id = int(parts[3])
    user_id = int(parts[4])
    
    # Зберігаємо дані в FSM
    await state.update_data(event_id=event_id, user_id=user_id)
    await state.set_state(KickPlayerStates.waiting_for_reason)
    
    await callback.message.edit_text(
        "🚫 <b>Кік учасника з події</b>\n\n"
        "Надішліть причину кіку (або напишіть 'пропустити' щоб не вказувати причину):",
        parse_mode="HTML"
    )
    await callback.answer()


@router.message(KickPlayerStates.waiting_for_reason)
@admin_only
async def admin_kick_participant_reason(message: Message, state: FSMContext):
    """Обробити причину кіку учасника з події"""
    reason = message.text.strip()
    
    if reason.lower() in ['пропустити', 'skip', 'немає', 'без причини']:
        reason = None
    
    await state.update_data(reason=reason)
    await state.set_state(KickPlayerStates.waiting_for_confirmation)
    
    # Отримуємо дані учасника
    data = await state.get_data()
    event_id = data['event_id']
    user_id = data['user_id']
    
    async for db_session in get_session():
        from sqlmodel import select
        from database.models import User, Event
        
        # Отримуємо дані учасника
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        participant = result.scalar_one_or_none()
        
        # Отримуємо дані події
        result = await db_session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not participant or not event:
            await message.answer("❌ Помилка: учасника або подію не знайдено.")
            await state.clear()
            return
        
        participant_name = participant.first_name
        if participant.last_name:
            participant_name += f" {participant.last_name}"
        
        text = f"🚫 <b>Підтвердження кіку</b>\n\n"
        text += f"👤 Учасник: <b>{participant_name}</b>\n"
        text += f"🎪 Подія: <b>{event.title}</b>\n"
        text += f"📅 Дата: {format_date(event.date)}\n"
        text += f"⏰ Час: {format_time(event.start_time)}\n\n"
        
        if reason:
            text += f"📝 Причина: <b>{reason}</b>\n\n"
        else:
            text += "📝 Причина: <b>не вказана</b>\n\n"
        
        text += "⚠️ Ви впевнені, що хочете кікнути цього учасника?"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так, кікнути", callback_data="confirm_kick_participant"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data="cancel_kick_participant")
            ]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "confirm_kick_participant")
@admin_only
async def admin_confirm_kick_participant(callback: CallbackQuery, state: FSMContext):
    """Підтвердити кік учасника з події"""
    data = await state.get_data()
    event_id = data['event_id']
    user_id = data['user_id']
    reason = data.get('reason')
    
    async for db_session in get_session():
        from sqlmodel import select
        from database.models import User, Event, EventRegistration
        
        # Отримуємо дані учасника
        result = await db_session.execute(
            select(User).where(User.id == user_id)
        )
        participant = result.scalar_one_or_none()
        
        # Отримуємо дані події
        result = await db_session.execute(
            select(Event).where(Event.id == event_id)
        )
        event = result.scalar_one_or_none()
        
        if not participant or not event:
            await callback.answer("❌ Помилка: учасника або подію не знайдено.", show_alert=True)
            await state.clear()
            return
        
        # Знаходимо реєстрацію
        result = await db_session.execute(
            select(EventRegistration).where(
                EventRegistration.event_id == event_id,
                EventRegistration.user_id == user_id,
                EventRegistration.is_active == True
            )
        )
        registration = result.scalar_one_or_none()
        
        if not registration:
            await callback.answer("❌ Помилка: реєстрацію не знайдено.", show_alert=True)
            await state.clear()
            return
        
        # Деактивуємо реєстрацію
        registration.is_active = False
        await db_session.commit()
        
        # Надсилаємо повідомлення учаснику
        participant_name = participant.first_name
        if participant.last_name:
            participant_name += f" {participant.last_name}"
        
        kick_message = f"🚫 <b>Вас кікнули з події</b>\n\n"
        kick_message += f"🎪 Подія: <b>{event.title}</b>\n"
        kick_message += f"📅 Дата: {format_date(event.date)}\n"
        kick_message += f"⏰ Час: {format_time(event.start_time)}\n\n"
        
        if reason:
            kick_message += f"📝 Причина: <b>{reason}</b>"
        else:
            kick_message += "📝 Причина не вказана"
        
        try:
            from aiogram import Bot
            from config import BOT_TOKEN
            bot = Bot(token=BOT_TOKEN)
            await bot.send_message(
                chat_id=participant.telegram_id,
                text=kick_message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Помилка надсилання повідомлення учаснику: {e}")
        
        await callback.message.edit_text(
            f"✅ Учасника <b>{participant_name}</b> успішно кікнуто з події!\n\n"
            f"📨 Повідомлення надіслано учаснику.",
            parse_mode="HTML"
        )
        
        await state.clear()
        await callback.answer()


@router.callback_query(F.data == "cancel_kick_participant")
@admin_only
async def admin_cancel_kick_participant(callback: CallbackQuery, state: FSMContext):
    """Скасувати кік учасника з події"""
    await callback.message.edit_text("❌ Кік учасника скасовано.")
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "admin_back_events_schedule")
async def admin_back_events_schedule(callback: CallbackQuery):
    """Повернутися до розкладу подій"""
    async for db_session in get_session():
        events = await EventService.get_upcoming_schedule(db_session, days=14)
        
        if not events:
            await callback.message.edit_text("📅 На найближчі 14 днів немає запланованих подій.")
            await callback.answer()
            return
        
        text = "🎪 <b>Розклад подій (Адмін)</b>\n\n"
        text += "Оберіть подію для управління:"
        
        # Створюємо клавіатуру з подіями
        keyboard = []
        
        for event in events:
            registrations = await get_event_registrations(db_session, event.id, active_only=True)
            participants_count = len(registrations)
            
            button_text = f"🎪 {event.title} | {format_date(event.date)} {format_time(event.start_time)} | {participants_count}/{event.max_participants}"
            
            keyboard.append([
                InlineKeyboardButton(
                    text=button_text,
                    callback_data=f"admin_manage_event_{event.id}"
                )
            ])
        
        kb = InlineKeyboardMarkup(inline_keyboard=keyboard)
        await callback.message.edit_text(text, reply_markup=kb, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("admin_delete_event_"))
async def admin_confirm_delete_event(callback: CallbackQuery):
    """Підтвердити видалення події"""
    event_id = int(callback.data.split("_")[-1])
    
    async for db_session in get_session():
        event = await EventService.get_event_by_id(db_session, event_id)
        
        if not event:
            await callback.answer("❌ Подію не знайдено", show_alert=True)
            return
        
        text = f"🗑️ <b>Підтвердження видалення</b>\n\n"
        text += f"🎪 Подія: <b>{event.title}</b>\n"
        text += f"📅 Дата: {format_date(event.date)}\n"
        text += f"⏰ Час: {format_time(event.start_time)} - {format_time(event.end_time)}\n\n"
        text += "⚠️ <b>Ви впевнені, що хочете видалити цю подію?</b>\n\n"
        text += "❌ Цю дію неможливо скасувати!"
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Так, видалити", callback_data=f"delete_event_confirmed_{event_id}"),
                InlineKeyboardButton(text="❌ Скасувати", callback_data=f"admin_manage_event_{event_id}")
            ]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data.startswith("delete_event_confirmed_"))
async def admin_delete_event_confirmed(callback: CallbackQuery):
    """Видалити подію після підтвердження"""
    event_id = int(callback.data.split("_")[-1])
    
    async for db_session in get_session():
        event = await EventService.get_event_by_id(db_session, event_id)
        
        if not event:
            await callback.answer("❌ Подію не знайдено", show_alert=True)
            return
        
        # Отримуємо всіх зареєстрованих користувачів
        registrations = await get_event_registrations(db_session, event_id, active_only=True)
        
        # Видаляємо подію
        await delete_event(db_session, event_id)
        
        # Надсилаємо повідомлення всім зареєстрованим користувачам
        if registrations:
            from sqlmodel import select
            from database.models import User
            from aiogram import Bot
            from config import BOT_TOKEN
            
            bot = Bot(token=BOT_TOKEN)
            
            cancel_message = f"❌ <b>Подію скасовано</b>\n\n"
            cancel_message += f"🎪 Подія: <b>{event.title}</b>\n"
            cancel_message += f"📅 Дата: {format_date(event.date)}\n"
            cancel_message += f"⏰ Час: {format_time(event.start_time)}\n\n"
            cancel_message += "Подію було видалено адміністратором."
            
            for reg in registrations:
                try:
                    result = await db_session.execute(
                        select(User).where(User.id == reg.user_id)
                    )
                    user = result.scalar_one_or_none()
                    
                    if user:
                        await bot.send_message(
                            chat_id=user.telegram_id,
                            text=cancel_message,
                            parse_mode="HTML"
                        )
                except Exception as e:
                    print(f"Помилка надсилання повідомлення користувачу {reg.user_id}: {e}")
        
        await callback.message.edit_text(
            f"✅ Подію <b>{event.title}</b> успішно видалено!\n\n"
            f"📨 Повідомлення надіслано всім зареєстрованим користувачам.",
            parse_mode="HTML"
        )
        await callback.answer()


# ===== КОРИСТУВАЧСЬКІ ОБРОБНИКИ =====

@router.message(F.text == "🎪 Події")
async def show_events_for_user(message: Message):
    """Показати події для користувача"""
    async for session in get_session():
        events = await EventService.get_upcoming_schedule(session, days=30)
        
        if not events:
            await message.answer("🎪 На найближчі дні немає запланованих подій.\n\nСлідкуйте за оновленнями!")
            return
        
        text = "🎪 <b>Доступні події:</b>\n\n"
        text += "Оберіть подію для реєстрації:"
        
        keyboard = get_events_list_keyboard(events, for_registration=True, page=0)
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data.startswith("event_register_"))
async def register_for_event(callback: CallbackQuery):
    """Зареєструватися на подію"""
    event_id = int(callback.data.split("_")[-1])
    user_telegram_id = callback.from_user.id
    
    async for session in get_session():
        from database import get_user_by_telegram_id
        
        # Отримуємо користувача
        user = await get_user_by_telegram_id(session, user_telegram_id)
        if not user:
            await callback.answer("❌ Помилка: користувача не знайдено", show_alert=True)
            return
        
        # Перевіряємо чи вже зареєстрований
        from database.crud import check_user_registered_for_event
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
            
            # Оновлюємо відображення події з новими кнопками
            await view_event_details_after_registration(callback, event_id)
        else:
            await callback.answer("❌ Не вдалося зареєструватися. Можливо, місця закінчилися.", show_alert=True)


@router.callback_query(F.data.startswith("event_cancel_"))
async def cancel_event_registration(callback: CallbackQuery):
    """Скасувати реєстрацію на подію"""
    event_id = int(callback.data.split("_")[-1])
    user_telegram_id = callback.from_user.id
    
    async for session in get_session():
        from database import get_user_by_telegram_id
        
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
            
            # Оновлюємо відображення події з новими кнопками
            await view_event_details_after_registration(callback, event_id)
        else:
            await callback.answer("❌ Не вдалося скасувати реєстрацію", show_alert=True)


@router.callback_query(F.data.startswith("event_participants_list_"))
async def show_event_participants_list(callback: CallbackQuery):
    """Показати список учасників події"""
    event_id = int(callback.data.split("_")[-1])
    
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
        registrations = await get_event_registrations(db_session, event_id, active_only=True)
        
        text = f"👥 <b>Список учасників</b>\n\n"
        text += f"🎪 Подія: <b>{event.title}</b>\n"
        text += f"📅 Дата: {format_date(event.date)}\n"
        text += f"⏰ Час: {format_time(event.start_time)} - {format_time(event.end_time)}\n\n"
        
        if not registrations:
            text += "Поки що ніхто не зареєстрований на цю подію."
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"view_event_{event_id}")]
            ])
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
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔙 Назад", callback_data=f"view_event_{event_id}")]
            ])
        
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


@router.message(F.text == "📋 Мої події")
async def show_my_events(message: Message):
    """Показати події користувача"""
    user_telegram_id = message.from_user.id
    
    async for session in get_session():
        from database import get_user_by_telegram_id
        
        # Отримуємо користувача
        user = await get_user_by_telegram_id(session, user_telegram_id)
        if not user:
            await message.answer("❌ Помилка: користувача не знайдено")
            return
        
        # Отримуємо реєстрації користувача
        registrations = await EventService.get_user_registrations(session, user.id)
        
        if not registrations:
            await message.answer("📋 У вас немає активних реєстрацій на події.")
            return
        
        text = "📋 <b>Ваші події:</b>\n\n"
        
        for reg in registrations:
            event = await EventService.get_event_by_id(session, reg.event_id)
            if event:
                text += f"🎪 <b>{event.title}</b>\n"
                text += f"📅 {format_date(event.date)} | ⏰ {format_time(event.start_time)} - {format_time(event.end_time)}\n\n"
        
        from keyboards import get_my_event_registrations_keyboard
        keyboard = get_my_event_registrations_keyboard(registrations)
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


# ===== РЕДАГУВАННЯ ПОДІЙ =====

@router.callback_query(F.data.startswith("start_edit_event_title_"))
async def start_edit_event_title(callback: CallbackQuery, state: FSMContext):
    """Почати редагування назви події"""
    event_id = int(callback.data.replace("start_edit_event_title_", ""))
    await state.update_data(edit_event_id=event_id)
    await state.set_state(EditEventStates.waiting_for_title)
    
    await callback.message.answer("✏️ Введіть нову назву події:")
    await callback.answer()


@router.message(EditEventStates.waiting_for_title)
async def process_edit_event_title(message: Message, state: FSMContext):
    """Обробка нової назви події"""
    data = await state.get_data()
    event_id = data.get("edit_event_id")
    
    async for session in get_session():
        event = await EventService.get_event_by_id(session, event_id)
        if event:
            await EventService.update_event_info(session, event, title=message.text)
            await message.answer(
                f"✅ Назву події змінено на: <b>{message.text}</b>",
                reply_markup=get_admin_events_menu(),
                parse_mode="HTML"
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("start_edit_event_description_"))
async def start_edit_event_description(callback: CallbackQuery, state: FSMContext):
    """Почати редагування опису події"""
    event_id = int(callback.data.replace("start_edit_event_description_", ""))
    await state.update_data(edit_event_id=event_id)
    await state.set_state(EditEventStates.waiting_for_description)
    
    await callback.message.answer("📝 Введіть новий опис події:")
    await callback.answer()


@router.message(EditEventStates.waiting_for_description)
async def process_edit_event_description(message: Message, state: FSMContext):
    """Обробка нового опису події"""
    data = await state.get_data()
    event_id = data.get("edit_event_id")
    
    async for session in get_session():
        event = await EventService.get_event_by_id(session, event_id)
        if event:
            await EventService.update_event_info(session, event, description=message.text)
            await message.answer(
                "✅ Опис події змінено!",
                reply_markup=get_admin_events_menu()
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("start_edit_event_date_"))
async def start_edit_event_date(callback: CallbackQuery, state: FSMContext):
    """Почати редагування дати події"""
    event_id = int(callback.data.replace("start_edit_event_date_", ""))
    await state.update_data(edit_event_id=event_id)
    await state.set_state(EditEventStates.waiting_for_date)
    
    text = "📅 <b>Оберіть нову дату проведення</b>\n\n"
    text += "Оберіть дату або введіть вручну (ДД.ММ.РРРР):"
    
    keyboard = get_date_selection_keyboard(prefix="select_event_date")
    
    await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
    await callback.answer()




@router.message(EditEventStates.waiting_for_date)
async def process_edit_custom_event_date(message: Message, state: FSMContext):
    """Обробка введеної нової дати для події"""
    valid, parsed_date, error_msg = validate_date(message.text)
    
    if not valid:
        await message.answer(error_msg)
        return
    
    data = await state.get_data()
    event_id = data.get("edit_event_id")
    
    async for session in get_session():
        event = await EventService.get_event_by_id(session, event_id)
        if event:
            await EventService.update_event_info(session, event, date=parsed_date)
            await message.answer(
                f"✅ Дату події змінено на: <b>{parsed_date.strftime('%d.%m.%Y')}</b>",
                parse_mode="HTML"
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("start_edit_event_time_"))
async def start_edit_event_time(callback: CallbackQuery, state: FSMContext):
    """Почати редагування часу події"""
    event_id = int(callback.data.replace("start_edit_event_time_", ""))
    await state.update_data(edit_event_id=event_id)
    await state.set_state(EditEventStates.waiting_for_start_time)
    
    await callback.message.answer("⏰ Введіть новий час початку (ЧЧ:ХХ):")
    await callback.answer()


@router.message(EditEventStates.waiting_for_start_time)
async def process_edit_event_start_time(message: Message, state: FSMContext):
    """Обробка нового часу початку події"""
    valid, parsed_time, error_msg = validate_time(message.text)
    
    if not valid:
        await message.answer(error_msg)
        return
    
    normalized_time = normalize_time(message.text)
    await state.update_data(start_time=normalized_time)
    await state.set_state(EditEventStates.waiting_for_end_time)
    await message.answer("⏰ Введіть новий час закінчення (ЧЧ:ХХ):")


@router.message(EditEventStates.waiting_for_end_time)
async def process_edit_event_end_time(message: Message, state: FSMContext):
    """Обробка нового часу закінчення події"""
    valid, parsed_time, error_msg = validate_time(message.text)
    
    if not valid:
        await message.answer(error_msg)
        return
    
    data = await state.get_data()
    start_time_str = data.get("start_time", "00:00")
    
    # Перевіряємо, що час закінчення пізніше початку
    start_valid, start_time_obj, _ = validate_time(start_time_str)
    if start_valid and start_time_obj >= parsed_time:
        await message.answer("⚠️ Час закінчення повинен бути пізніше часу початку")
        return
    
    normalized_time = normalize_time(message.text)
    
    # Конвертуємо строки у time об'єкти
    from datetime import time as dt_time
    start_time_obj = dt_time.fromisoformat(start_time_str)
    end_time_obj = dt_time.fromisoformat(normalized_time)
    
    event_id = data.get("edit_event_id")
    
    async for session in get_session():
        event = await EventService.get_event_by_id(session, event_id)
        if event:
            await EventService.update_event_info(
                session, event, 
                start_time=start_time_obj, 
                end_time=end_time_obj
            )
            await message.answer(
                f"✅ Час події змінено на: <b>{start_time_str} - {normalized_time}</b>",
                parse_mode="HTML"
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("start_edit_event_participants_"))
async def start_edit_event_participants(callback: CallbackQuery, state: FSMContext):
    """Почати редагування кількості учасників події"""
    event_id = int(callback.data.replace("start_edit_event_participants_", ""))
    await state.update_data(edit_event_id=event_id)
    await state.set_state(EditEventStates.waiting_for_min_participants)
    
    await callback.message.answer("👥 Введіть нову мінімальну кількість учасників:")
    await callback.answer()


@router.message(EditEventStates.waiting_for_min_participants)
async def process_edit_event_min_participants(message: Message, state: FSMContext):
    """Обробка нової мінімальної кількості учасників"""
    try:
        min_participants = int(message.text)
        if min_participants < 1:
            await message.answer("⚠️ Мінімальна кількість учасників повинна бути більше 0")
            return
        
        await state.update_data(min_participants=min_participants)
        await state.set_state(EditEventStates.waiting_for_max_participants)
        await message.answer("👥 Введіть нову максимальну кількість учасників:")
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.message(EditEventStates.waiting_for_max_participants)
async def process_edit_event_max_participants(message: Message, state: FSMContext):
    """Обробка нової максимальної кількості учасників"""
    try:
        max_participants = int(message.text)
        data = await state.get_data()
        min_participants = data.get("min_participants", 1)
        
        # Валідація
        valid, error_msg = validate_players_count(min_participants, max_participants)
        if not valid:
            await message.answer(error_msg)
            return
        
        event_id = data.get("edit_event_id")
        
        async for session in get_session():
            event = await EventService.get_event_by_id(session, event_id)
            if event:
                await EventService.update_event_info(
                    session, event,
                    min_participants=min_participants,
                    max_participants=max_participants
                )
                await message.answer(
                    f"✅ Кількість учасників змінено на: <b>{min_participants}-{max_participants}</b>",
                    parse_mode="HTML"
                )
        
        await state.clear()
    except ValueError:
        await message.answer("⚠️ Будь ласка, введіть число")


@router.callback_query(F.data.startswith("start_edit_event_payment_"))
async def start_edit_event_payment(callback: CallbackQuery, state: FSMContext):
    """Почати редагування типу оплати події"""
    # Видаляємо префікс "start_edit_event_payment_" і отримуємо event_id
    event_id = int(callback.data.replace("start_edit_event_payment_", ""))
    await state.update_data(edit_event_id=event_id)
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Входить в оплату за вхід", callback_data="edit_event_payment_included")],
        [InlineKeyboardButton(text="🎁 Безкоштовна", callback_data="edit_event_payment_free")],
        [InlineKeyboardButton(text="💝 Free donate", callback_data="edit_event_payment_donate")]
    ])
    
    await callback.message.answer(
        "💳 Оберіть новий тип оплати для події:",
        reply_markup=keyboard
    )
    await callback.answer()


@router.callback_query(F.data.in_(["edit_event_payment_included", "edit_event_payment_free", "edit_event_payment_donate"]))
async def process_edit_event_payment(callback: CallbackQuery, state: FSMContext):
    """Обробка нового типу оплати події"""
    payment_types = {
        "edit_event_payment_included": "included",
        "edit_event_payment_free": "free",
        "edit_event_payment_donate": "donate"
    }
    
    payment_type = payment_types[callback.data]
    data = await state.get_data()
    event_id = data.get("edit_event_id")
    
    async for session in get_session():
        event = await EventService.get_event_by_id(session, event_id)
        if event:
            await EventService.update_event_info(session, event, payment_type=payment_type)
            
            payment_type_text = {
                "included": "✅ Входить в оплату за вхід",
                "free": "🎁 Безкоштовна",
                "donate": "💝 Free donate"
            }
            
            await callback.message.edit_text(
                f"✅ Тип оплати змінено на: <b>{payment_type_text.get(payment_type, 'Входить в оплату')}</b>",
                parse_mode="HTML"
            )
    
    await state.clear()
    await callback.answer()


@router.callback_query(F.data.startswith("start_edit_event_image_"))
async def start_edit_event_image(callback: CallbackQuery, state: FSMContext):
    """Почати редагування зображення події"""
    event_id = int(callback.data.replace("start_edit_event_image_", ""))
    await state.update_data(edit_event_id=event_id)
    await state.set_state(EditEventStates.waiting_for_image)
    
    await callback.message.answer("📸 Надішліть нове зображення події:")
    await callback.answer()


@router.message(EditEventStates.waiting_for_image, F.photo)
async def process_edit_event_image(message: Message, state: FSMContext):
    """Обробка нового зображення події"""
    import logging
    
    photo = message.photo[-1]
    file_id = photo.file_id
    
    data = await state.get_data()
    event_id = data.get("edit_event_id")
    
    logging.info(f"✅ Оновлено Telegram file_id для події {event_id}: {file_id}")
    
    async for session in get_session():
        event = await EventService.get_event_by_id(session, event_id)
        if event:
            await EventService.update_event_info(session, event, image_file_id=file_id)
            await message.answer(
                "✅ Зображення події змінено!",
                reply_markup=get_admin_events_menu()
            )
    
    await state.clear()


@router.callback_query(F.data.startswith("delete_event_"))
async def confirm_delete_event(callback: CallbackQuery):
    """Підтвердження видалення події"""
    event_id = int(callback.data.split("_")[-1])
    
    async for session in get_session():
        event = await EventService.get_event_by_id(session, event_id)
        if not event:
            await callback.answer("❌ Подію не знайдено", show_alert=True)
            return
        
        from keyboards import get_confirmation_keyboard
        text = f"⚠️ Ви впевнені що хочете видалити подію <b>{event.title}</b>?\n\n"
        text += "Це також видалить всі реєстрації на цю подію.\n"
        text += "Користувачі, зареєстровані на цю подію, отримають сповіщення про скасування."
        
        keyboard = get_confirmation_keyboard("delete_event", event_id)
        
        # Перевіряємо чи є фото в попередньому повідомленні
        has_photo = callback.message.photo is not None and len(callback.message.photo) > 0
        
        if has_photo:
            # Якщо попереднє повідомлення містило фото, видаляємо його і відправляємо нове
            await callback.message.delete()
            await callback.message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            # Якщо попереднє повідомлення було текстовим, редагуємо його
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        
        await callback.answer()


@router.callback_query(F.data.startswith("confirm_delete_event_"))
async def delete_event_confirmed(callback: CallbackQuery):
    """Видалити подію після підтвердження"""
    event_id = int(callback.data.split("_")[-1])
    
    async for session in get_session():
        success = await EventService.delete_event(session, event_id)
        if success:
            # Перевіряємо чи є фото в попередньому повідомленні
            has_photo = callback.message.photo is not None and len(callback.message.photo) > 0
            
            if has_photo:
                # Якщо попереднє повідомлення містило фото, видаляємо його і відправляємо нове
                await callback.message.delete()
                await callback.message.answer("✅ Подію успішно видалено!")
            else:
                # Якщо попереднє повідомлення було текстовим, редагуємо його
                await callback.message.edit_text("✅ Подію успішно видалено!")
            
            await callback.answer()
        else:
            await callback.answer("❌ Помилка при видаленні події", show_alert=True)


async def view_event_details_after_registration(callback: CallbackQuery, event_id: int):
    """Оновити відображення події після реєстрації/скасування"""
    user_telegram_id = callback.from_user.id
    
    async for db_session in get_session():
        from database import get_user_by_telegram_id
        from services import EventService
        from database.crud import check_user_registered_for_event, get_event_registrations
        
        # Отримуємо користувача
        user = await get_user_by_telegram_id(db_session, user_telegram_id)
        if not user:
            return
        
        # Отримуємо подію
        event = await EventService.get_event_by_id(db_session, event_id)
        if not event:
            return
        
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
        
        # Створюємо клавіатуру
        from keyboards import get_event_actions_keyboard
        keyboard = get_event_actions_keyboard(event_id, is_registered=is_registered)
        
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
                    # Якщо не вдалося відправити фото, відправляємо тільки текст
                    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
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
