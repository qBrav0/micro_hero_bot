from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from database import get_session, get_user_by_telegram_id, update_user
from keyboards import get_main_menu
from config import ADMIN_IDS

router = Router()


class ReminderSettings(StatesGroup):
    """Стани для налаштування нагадувань"""
    waiting_for_hours = State()


@router.message(F.text == "🔔 Налаштування нагадувань")
async def show_reminder_settings(message: Message):
    """Показати меню налаштувань нагадувань"""
    user_id = message.from_user.id
    
    async for session in get_session():
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await message.answer("Помилка: користувача не знайдено")
            return
        
        # Формуємо текст з поточними налаштуваннями
        text = "🔔 <b>Налаштування нагадувань</b>\n\n"
        
        if user.reminder_enabled and user.reminder_hours_before:
            text += f"✅ <b>Статус:</b> Увімкнено\n"
            text += f"⏰ <b>Нагадувати за:</b> {user.reminder_hours_before} год.\n\n"
        else:
            text += "❌ <b>Статус:</b> Вимкнено\n\n"
        
        text += "💡 <b>Як це працює:</b>\n"
        text += "• Ви отримаєте нагадування за вказану кількість годин до початку сесії\n"
        text += "• Якщо у вас є кілька записів на один день, ви отримаєте одне нагадування\n"
        text += "• Нагадування прийде за вказаний час до першої сесії цього дня\n"
        text += "• У нагадуванні буде інформація про всі ваші записи на цей день\n\n"
        text += "Оберіть дію:"
        
        # Клавіатура
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Увімкнути нагадування",
                    callback_data="reminder_enable"
                )
            ],
            [
                InlineKeyboardButton(
                    text="❌ Вимкнути нагадування",
                    callback_data="reminder_disable"
                )
            ]
        ])
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "reminder_disable")
async def disable_reminders(callback: CallbackQuery):
    """Вимкнути нагадування"""
    user_id = callback.from_user.id
    
    async for session in get_session():
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await callback.answer("Помилка: користувача не знайдено", show_alert=True)
            return
        
        # Вимикаємо нагадування
        user.reminder_enabled = False
        user.reminder_hours_before = None
        await update_user(session, user)
        
        text = "❌ <b>Нагадування вимкнено</b>\n\n"
        text += "Ви більше не будете отримувати нагадування про записи.\n"
        text += "Ви можете увімкнути їх знову в будь-який час через меню налаштувань."
        
        await callback.message.edit_text(text, parse_mode="HTML")
        await callback.answer("Нагадування вимкнено")


@router.callback_query(F.data == "reminder_enable")
async def enable_reminders(callback: CallbackQuery, state: FSMContext):
    """Увімкнути нагадування - запитати кількість годин"""
    text = "⏰ <b>Налаштування часу нагадування</b>\n\n"
    text += "Введіть за скільки годин до початку сесії ви хочете отримувати нагадування.\n\n"
    text += "💡 <b>Важливо:</b>\n"
    text += "• Якщо у вас є кілька записів на один день, нагадування прийде за вказаний час до першої (найранішої) сесії\n"
    text += "• У цьому нагадуванні буде інформація про всі ваші записи на цей день\n\n"
    text += "Наприклад, якщо ввести <code>3</code>, ви отримаєте нагадування за 3 години до початку першої сесії дня.\n\n"
    text += "📝 <b>Введіть кількість годин (число від 1 до 72):</b>"
    
    # Кнопка скасування
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(
                text="❌ Скасувати",
                callback_data="reminder_cancel"
            )
        ]
    ])
    
    await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    await state.set_state(ReminderSettings.waiting_for_hours)
    await callback.answer()


@router.callback_query(F.data == "reminder_cancel")
async def cancel_reminder_setup(callback: CallbackQuery, state: FSMContext):
    """Скасувати налаштування нагадування"""
    await state.clear()
    
    text = "❌ <b>Налаштування скасовано</b>\n\n"
    text += "Ви можете налаштувати нагадування в будь-який час через головне меню."
    
    await callback.message.edit_text(text, parse_mode="HTML")
    await callback.answer("Скасовано")


@router.message(ReminderSettings.waiting_for_hours)
async def process_reminder_hours(message: Message, state: FSMContext):
    """Обробити введену кількість годин"""
    user_id = message.from_user.id
    
    # Перевіряємо чи це число
    try:
        hours = int(message.text.strip())
    except ValueError:
        await message.answer(
            "❌ Помилка! Введіть ціле число.\n\n"
            "Наприклад: 3"
        )
        return
    
    # Перевіряємо діапазон
    if hours < 1 or hours > 72:
        await message.answer(
            "❌ Помилка! Кількість годин має бути від 1 до 72.\n\n"
            "Введіть коректне число:"
        )
        return
    
    # Зберігаємо налаштування
    async for session in get_session():
        user = await get_user_by_telegram_id(session, user_id)
        if not user:
            await message.answer("Помилка: користувача не знайдено")
            await state.clear()
            return
        
        user.reminder_enabled = True
        user.reminder_hours_before = hours
        await update_user(session, user)
        
        text = "✅ <b>Нагадування налаштовано!</b>\n\n"
        text += f"⏰ Ви будете отримувати нагадування за <b>{hours} год.</b> до початку сесії.\n\n"
        text += "💡 <b>Пам'ятайте:</b>\n"
        text += "• Якщо у вас кілька записів на один день, нагадування прийде одне\n"
        text += f"• Воно прийде за {hours} год. до першої (найранішої) сесії дня\n"
        text += "• У ньому буде інформація про всі ваші записи на цей день\n\n"
        text += "Ви можете змінити налаштування в будь-який час через меню 🔔 Налаштування нагадувань."
        
        await message.answer(text, parse_mode="HTML")
        await state.clear()

