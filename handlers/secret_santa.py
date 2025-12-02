from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging

from database import get_session, get_user_by_telegram_id
from database.crud import (
    create_secret_santa_participant,
    get_secret_santa_participant,
    check_secret_santa_registered,
    get_all_secret_santa_participants
)
from keyboards.inline_keyboards import (
    get_secret_santa_main_keyboard,
    get_secret_santa_registered_keyboard
)
from keyboards import get_main_menu
from config import ADMIN_IDS, BOT_TOKEN

router = Router()
logger = logging.getLogger(__name__)


class SecretSantaStates(StatesGroup):
    """Стани для реєстрації в Таємному Санті"""
    waiting_for_wishes = State()


@router.message(F.text == "🎅 Таємний Санта")
async def show_secret_santa_info(message: Message):
    """Показати інформацію про Таємний Санта"""
    user_id = message.from_user.id
    
    async for session in get_session():
        # Перевіряємо чи користувач вже зареєстрований
        is_registered = await check_secret_santa_registered(session, 
                                                            await get_user_id_by_telegram_id(session, user_id))
        
        # Опис Таємного Санти
        text = "🎅 <b>Таємний Санта</b> 🎄\n\n"
        text += "Таємний Санта — це чудова передноворічна традиція обміну подарунками!\n\n"
        text += "📝 <b>Як це працює?</b>\n"
        text += "1️⃣ Ви реєструєтесь і вказуєте свої побажання щодо подарунка\n"
        text += "2️⃣ Через 3 дні відбудеться жеребкування\n"
        text += "3️⃣ Ви дізнаєтесь, кому маєте подарувати подарунок\n"
        text += "4️⃣ Готуєте подарунок згідно з побажаннями цієї особи\n\n"
        text += "💰 <b>Рекомендована вартість:</b> 200-300 грн\n"
        text += "   (за бажанням можна подарувати за більшу вартість)\n\n"
        
        if is_registered:
            text += "✅ <b>Ви вже зареєстровані!</b>\n"
            text += "Очікуйте на результати жеребкування через 3 дні! 🎁"
            keyboard = get_secret_santa_registered_keyboard()
        else:
            text += "👇 Натисніть кнопку нижче, щоб взяти участь!"
            keyboard = get_secret_santa_main_keyboard()
        
        await message.answer(text, reply_markup=keyboard, parse_mode="HTML")


@router.callback_query(F.data == "secret_santa_participate")
async def start_participation(callback: CallbackQuery, state: FSMContext):
    """Початок процесу реєстрації"""
    user_id = callback.from_user.id
    
    async for session in get_session():
        # Перевіряємо чи користувач вже зареєстрований
        user_db = await get_user_by_telegram_id(session, user_id)
        if not user_db:
            await callback.message.edit_text("❌ Помилка: користувача не знайдено")
            await callback.answer()
            return
        
        is_registered = await check_secret_santa_registered(session, user_db.id)
        
        if is_registered:
            await callback.message.edit_text(
                "✅ Ви вже зареєстровані в Таємному Санті!\n\n"
                "Очікуйте на результати жеребкування через 3 дні! 🎁",
                parse_mode="HTML"
            )
            await callback.answer()
            return
        
        # Запитуємо побажання
        text = "🎁 <b>Реєстрація в Таємному Санті</b>\n\n"
        text += "Будь ласка, напишіть свої побажання щодо подарунка.\n\n"
        text += "💡 <b>Наприклад:</b>\n"
        text += "• Книга з фентезі\n"
        text += "• Настільна гра для компанії\n"
        text += "• Солодощі та чай\n"
        text += "• Аксесуари для хобі\n\n"
        text += "💰 <b>Пам'ятайте:</b> орієнтовна вартість подарунків 200-300 грн\n"
        text += "   (за бажанням можна подарувати за більшу вартість)\n\n"
        text += "✍️ Напишіть ваші побажання:"
        
        await callback.message.edit_text(text, parse_mode="HTML")
        await state.set_state(SecretSantaStates.waiting_for_wishes)
        await callback.answer()


@router.message(SecretSantaStates.waiting_for_wishes)
async def process_wishes(message: Message, state: FSMContext):
    """Обробка побажань користувача"""
    user_id = message.from_user.id
    wishes = message.text
    
    # Перевіряємо чи побажання не занадто короткі
    if len(wishes) < 10:
        await message.answer(
            "❌ Побажання занадто короткі!\n\n"
            "Будь ласка, опишіть детальніше, що б ви хотіли отримати в подарунок (мінімум 10 символів)."
        )
        return
    
    async for session in get_session():
        user_db = await get_user_by_telegram_id(session, user_id)
        if not user_db:
            await message.answer("❌ Помилка: користувача не знайдено")
            await state.clear()
            return
        
        # Перевіряємо чи користувач вже не зареєстрований
        is_registered = await check_secret_santa_registered(session, user_db.id)
        if is_registered:
            await message.answer(
                "✅ Ви вже зареєстровані в Таємному Санті!",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        # Реєструємо учасника
        try:
            await create_secret_santa_participant(session, user_db.id, wishes)
            
            text = "✅ <b>Вітаємо! Ви зареєстровані!</b> 🎉\n\n"
            text += f"📝 <b>Ваші побажання:</b>\n{wishes}\n\n"
            text += "🎲 <b>Що далі?</b>\n"
            text += "• Жеребкування відбудеться через 3 дні\n"
            text += "• Ви отримаєте повідомлення з інформацією про вашого підопічного\n"
            text += "• Приготуйте подарунок відповідно до його побажань\n\n"
            text += "🎁 Дякуємо за участь! З нетерпінням чекаємо на свято!"
            
            is_admin = message.from_user.id in ADMIN_IDS
            await message.answer(text, parse_mode="HTML")
            await message.answer(
                "Повертайтесь до головного меню:",
                reply_markup=get_main_menu(is_admin=is_admin)
            )
            
            # Відправляємо сповіщення адмінам
            await notify_admins_about_registration(
                user_first_name=message.from_user.first_name,
                user_last_name=message.from_user.last_name,
                username=message.from_user.username
            )
            
            await state.clear()
            
        except Exception as e:
            await message.answer(
                f"❌ Помилка при реєстрації: {e}\n\n"
                "Спробуйте ще раз або зверніться до адміністратора."
            )
            await state.clear()


@router.callback_query(F.data == "secret_santa_already_registered")
async def already_registered(callback: CallbackQuery):
    """Обробка натискання на кнопку для вже зареєстрованих"""
    await callback.answer("Ви вже зареєстровані! 🎁", show_alert=True)


@router.message(F.text == "🎅 Таємний Санта (адмін)")
async def show_secret_santa_admin(message: Message):
    """Показати адмін-панель Таємного Санти"""
    user_id = message.from_user.id
    
    # Перевіряємо чи користувач адмін
    if user_id not in ADMIN_IDS:
        await message.answer("❌ У вас немає доступу до цієї функції")
        return
    
    async for session in get_session():
        # Отримуємо всіх учасників
        participants = await get_all_secret_santa_participants(session)
        
        if not participants:
            text = "🎅 <b>Таємний Санта - Адмін-панель</b>\n\n"
            text += "📋 Поки що немає зареєстрованих учасників."
            await message.answer(text, parse_mode="HTML")
            return
        
        # Формуємо список учасників
        text = "🎅 <b>Таємний Санта - Адмін-панель</b>\n\n"
        text += f"👥 <b>Всього учасників:</b> {len(participants)}\n\n"
        text += "📋 <b>Список учасників:</b>\n\n"
        
        from database.models import User
        from sqlmodel import select
        
        for idx, participant in enumerate(participants, 1):
            # Отримуємо інформацію про користувача
            result = await session.execute(
                select(User).where(User.id == participant.user_id)
            )
            user = result.scalar_one_or_none()
            
            if user:
                username = f"@{user.username}" if user.username else "немає username"
                full_name = user.first_name
                if user.last_name:
                    full_name += f" {user.last_name}"
                
                text += f"{idx}. <b>{full_name}</b> ({username})\n"
                text += f"   📝 Побажання: {participant.wishes}\n"
                text += f"   📅 Зареєстрований: {participant.registered_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        
        await message.answer(text, parse_mode="HTML")


async def notify_admins_about_registration(user_first_name: str, user_last_name: str, username: str):
    """Відправити сповіщення адмінам про нову реєстрацію"""
    try:
        bot = Bot(token=BOT_TOKEN)
        
        full_name = user_first_name
        if user_last_name:
            full_name += f" {user_last_name}"
        
        username_text = f"@{username}" if username else "немає username"
        
        notification_text = "🎅 <b>Нова реєстрація на Таємного Санту!</b>\n\n"
        notification_text += f"👤 <b>Користувач:</b> {full_name}\n"
        notification_text += f"📱 <b>Username:</b> {username_text}\n"
        
        # Відправляємо кожному адміну
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(
                    chat_id=admin_id,
                    text=notification_text,
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Помилка відправки повідомлення адміну {admin_id}: {e}")
        
        await bot.session.close()
        
    except Exception as e:
        logger.error(f"Помилка при відправці сповіщень адмінам: {e}")


async def get_user_id_by_telegram_id(session: AsyncSession, telegram_id: int) -> int:
    """Допоміжна функція для отримання ID користувача з БД"""
    user = await get_user_by_telegram_id(session, telegram_id)
    return user.id if user else None

