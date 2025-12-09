from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import datetime, timedelta
import logging
import random

from database import get_session, get_user_by_telegram_id
from database.crud import (
    create_secret_santa_participant,
    get_secret_santa_participant,
    check_secret_santa_registered,
    get_all_secret_santa_participants,
    update_secret_santa_assignment
)
from keyboards.inline_keyboards import (
    get_secret_santa_main_keyboard,
    get_secret_santa_registered_keyboard
)
from keyboards import get_main_menu
from config import ADMIN_IDS, BOT_TOKEN

router = Router()
logger = logging.getLogger(__name__)

# Глобальна змінна для збереження результатів жеребкування
draw_results = {}


class SecretSantaStates(StatesGroup):
    """Стани для реєстрації в Таємному Санті"""
    waiting_for_wishes = State()


@router.message(F.text == "🎅 Таємний Санта")
async def show_secret_santa_info(message: Message):
    """Показати інформацію про Таємний Санта"""
    user_id = message.from_user.id
    
    async for session in get_session():
        user_db = await get_user_by_telegram_id(session, user_id)
        if not user_db:
            await message.answer("❌ Помилка: користувача не знайдено")
            return
        
        # Перевіряємо чи користувач вже зареєстрований
        participant = await get_secret_santa_participant(session, user_db.id)
        
        if participant and participant.draw_completed and participant.assigned_to:
            # Жеребкування відбулось - показуємо інформацію про підопічного
            from database.models import User
            from sqlmodel import select
            
            result = await session.execute(
                select(User).where(User.id == participant.assigned_to)
            )
            assigned_user = result.scalar_one_or_none()
            
            if assigned_user:
                # Отримуємо побажання підопічного
                assigned_participant = await get_secret_santa_participant(session, assigned_user.id)
                
                text = "🎅 <b>Ваш таємний підопічний!</b> 🎁\n\n"
                text += f"👤 <b>Ім'я:</b> {assigned_user.first_name}"
                if assigned_user.last_name:
                    text += f" {assigned_user.last_name}"
                text += "\n"
                
                if assigned_user.username:
                    text += f"📱 <b>Контакт:</b> @{assigned_user.username}\n\n"
                else:
                    text += "📱 <b>Контакт:</b> попросіть у адміністратора\n\n"
                
                if assigned_participant:
                    text += f"📝 <b>Побажання:</b>\n{assigned_participant.wishes}\n\n"
                
                text += "🎁 <b>Дата обміну подарунками:</b> 28.12 в ігротеці\n\n"
                text += "💰 <b>Рекомендована вартість:</b> 200-300 грн\n"
                text += "   (за бажанням можна подарувати за більшу вартість)"
                
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="🔄 Переглянути знову", callback_data="secret_santa_show_assigned")]
                ])
                
                await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
            else:
                await message.answer("❌ Помилка отримання інформації про підопічного")
        
        elif participant:
            # Зареєстрований, але жеребкування ще не відбулось
            text = "🎅 <b>Таємний Санта</b> 🎄\n\n"
            text += "✅ <b>Ви вже зареєстровані!</b>\n\n"
            text += "📝 <b>Ваші побажання:</b>\n"
            text += f"{participant.wishes}\n\n"
            text += "⏳ Очікуйте на результати жеребкування!"
            keyboard = get_secret_santa_registered_keyboard()
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        
        else:
            # Не зареєстрований
            text = "🎅 <b>Таємний Санта</b> 🎄\n\n"
            text += "Таємний Санта — це чудова передноворічна традиція обміну подарунками!\n\n"
            text += "📝 <b>Як це працює?</b>\n"
            text += "1️⃣ Ви реєструєтесь і вказуєте свої побажання щодо подарунка\n"
            text += "2️⃣ Через 3 дні відбудеться жеребкування\n"
            text += "3️⃣ Ви дізнаєтесь, кому маєте подарувати подарунок\n"
            text += "4️⃣ Готуєте подарунок згідно з побажаннями цієї особи\n\n"
            text += "💰 <b>Рекомендована вартість:</b> 200-300 грн\n"
            text += "   (за бажанням можна подарувати за більшу вартість)\n\n"
            text += "🎁 <b>Дата обміну подарунками:</b> 28.12 в ігротеці\n\n"
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


@router.callback_query(F.data == "secret_santa_show_assigned")
async def show_assigned_info(callback: CallbackQuery):
    """Повторний перегляд інформації про підопічного"""
    user_id = callback.from_user.id
    
    async for session in get_session():
        user_db = await get_user_by_telegram_id(session, user_id)
        if not user_db:
            await callback.message.edit_text("❌ Помилка: користувача не знайдено")
            await callback.answer()
            return
        
        participant = await get_secret_santa_participant(session, user_db.id)
        
        if not participant or not participant.draw_completed or not participant.assigned_to:
            await callback.answer("❌ Жеребкування ще не відбулось", show_alert=True)
            return
        
        from database.models import User
        from sqlmodel import select
        
        result = await session.execute(
            select(User).where(User.id == participant.assigned_to)
        )
        assigned_user = result.scalar_one_or_none()
        
        if assigned_user:
            # Отримуємо побажання підопічного
            assigned_participant = await get_secret_santa_participant(session, assigned_user.id)
            
            text = "🎅 <b>Ваш таємний підопічний!</b> 🎁\n\n"
            text += f"👤 <b>Ім'я:</b> {assigned_user.first_name}"
            if assigned_user.last_name:
                text += f" {assigned_user.last_name}"
            text += "\n"
            
            if assigned_user.username:
                text += f"📱 <b>Контакт:</b> @{assigned_user.username}\n\n"
            else:
                text += "📱 <b>Контакт:</b> попросіть у адміністратора\n\n"
            
            if assigned_participant:
                text += f"📝 <b>Побажання:</b>\n{assigned_participant.wishes}\n\n"
            
            text += "🎁 <b>Дата обміну подарунками:</b> 28.12 в ігротеці\n\n"
            text += "💰 <b>Рекомендована вартість:</b> 200-300 грн\n"
            text += "   (за бажанням можна подарувати за більшу вартість)"
            
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🔄 Переглянути знову", callback_data="secret_santa_show_assigned")]
            ])
            
            await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
            await callback.answer()
        else:
            await callback.answer("❌ Помилка отримання інформації", show_alert=True)


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
        
        # Перевіряємо чи відбулось жеребкування
        draw_completed = any(p.draw_completed for p in participants)
        
        # Формуємо список учасників
        text = "🎅 <b>Таємний Санта - Адмін-панель</b>\n\n"
        text += f"👥 <b>Всього учасників:</b> {len(participants)}\n"
        
        if draw_completed:
            text += "✅ <b>Статус:</b> Жеребкування проведено\n\n"
        else:
            text += "⏳ <b>Статус:</b> Очікування жеребкування\n\n"
        
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
        
        # Додаємо кнопку жеребкування якщо воно ще не відбулось
        if not draw_completed:
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🎲 Провести жеребкування", callback_data="secret_santa_start_draw")]
            ])
            text += "\n💡 Натисніть кнопку нижче для проведення жеребкування"
            await message.answer(text, reply_markup=keyboard, parse_mode="HTML")
        else:
            text += "\n✅ <b>Жеребкування завершено!</b>\n"
            text += "📤 Всі учасники отримали повідомлення з інформацією про своїх підопічних.\n"
            text += "🔒 Повторне жеребкування неможливе."
            await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "secret_santa_start_draw")
async def start_draw(callback: CallbackQuery):
    """Початок жеребкування"""
    user_id = callback.from_user.id
    
    # Перевіряємо чи користувач адмін
    if user_id not in ADMIN_IDS:
        await callback.answer("❌ У вас немає доступу до цієї функції", show_alert=True)
        return
    
    async for session in get_session():
        participants = await get_all_secret_santa_participants(session)
        
        if len(participants) < 2:
            await callback.answer("❌ Недостатньо учасників для жеребкування (мінімум 2)", show_alert=True)
            return
        
        # Перевіряємо чи жеребкування вже відбулось
        if any(p.draw_completed for p in participants):
            await callback.answer("❌ Жеребкування вже було проведено", show_alert=True)
            return
        
        # Проводимо жеребкування
        pairs = conduct_draw(participants)
        
        # Зберігаємо результати в глобальній змінній
        draw_results[user_id] = pairs
        
        # Формуємо повідомлення з результатами
        from database.models import User
        from sqlmodel import select
        
        text = "🎲 <b>Результати жеребкування</b>\n\n"
        text += "Перевірте чи коректно сформовані пари:\n\n"
        
        for giver_id, receiver_id in pairs:
            # Отримуємо інформацію про дарувальника
            result = await session.execute(select(User).where(User.id == giver_id))
            giver = result.scalar_one_or_none()
            
            # Отримуємо інформацію про отримувача
            result = await session.execute(select(User).where(User.id == receiver_id))
            receiver = result.scalar_one_or_none()
            
            if giver and receiver:
                giver_name = giver.first_name
                if giver.last_name:
                    giver_name += f" {giver.last_name}"
                
                receiver_name = receiver.first_name
                if receiver.last_name:
                    receiver_name += f" {receiver.last_name}"
                
                text += f"🎁 <b>{giver_name}</b> → <b>{receiver_name}</b>\n"
        
        text += "\n❓ Якщо все правильно, натисніть кнопку нижче для розсилки повідомлень учасникам."
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📤 Розіслати повідомлення", callback_data="secret_santa_send_notifications")],
            [InlineKeyboardButton(text="🔄 Повторити жеребкування", callback_data="secret_santa_start_draw")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
        await callback.answer()


@router.callback_query(F.data == "secret_santa_send_notifications")
async def send_draw_notifications(callback: CallbackQuery):
    """Розсилка повідомлень учасникам після жеребкування"""
    user_id = callback.from_user.id
    
    # Перевіряємо чи користувач адмін
    if user_id not in ADMIN_IDS:
        await callback.answer("❌ У вас немає доступу до цієї функції", show_alert=True)
        return
    
    # Перевіряємо чи є збережені результати жеребкування
    if user_id not in draw_results:
        await callback.answer("❌ Результати жеребкування не знайдені. Проведіть жеребкування спочатку.", show_alert=True)
        return
    
    pairs = draw_results[user_id]
    
    async for session in get_session():
        # ДОДАТКОВА ПЕРЕВІРКА: чи жеребкування вже не було проведено
        participants = await get_all_secret_santa_participants(session)
        if any(p.draw_completed for p in participants):
            await callback.answer("❌ Жеребкування вже було проведено раніше!", show_alert=True)
            # Очищаємо збережені результати
            if user_id in draw_results:
                del draw_results[user_id]
            return
        
        try:
            # Зберігаємо результати в БД
            for giver_id, receiver_id in pairs:
                await update_secret_santa_assignment(session, giver_id, receiver_id)
            
            # Відправляємо повідомлення учасникам
            bot = Bot(token=BOT_TOKEN)
            
            from database.models import User
            from sqlmodel import select
            
            success_count = 0
            for giver_id, receiver_id in pairs:
                # Отримуємо інформацію про дарувальника
                result = await session.execute(select(User).where(User.id == giver_id))
                giver = result.scalar_one_or_none()
                
                # Отримуємо інформацію про отримувача
                result = await session.execute(select(User).where(User.id == receiver_id))
                receiver = result.scalar_one_or_none()
                
                if giver and receiver:
                    # Отримуємо побажання отримувача
                    receiver_participant = await get_secret_santa_participant(session, receiver.id)
                    
                    # Формуємо повідомлення
                    message_text = "🎅 <b>Жеребкування Таємного Санти!</b> 🎁\n\n"
                    message_text += "🎉 Результати жеребкування готові!\n\n"
                    message_text += f"👤 <b>Ваш підопічний:</b> {receiver.first_name}"
                    if receiver.last_name:
                        message_text += f" {receiver.last_name}"
                    message_text += "\n"
                    
                    if receiver.username:
                        message_text += f"📱 <b>Контакт:</b> @{receiver.username}\n\n"
                    else:
                        message_text += "📱 <b>Контакт:</b> попросіть у адміністратора\n\n"
                    
                    if receiver_participant:
                        message_text += f"📝 <b>Побажання:</b>\n{receiver_participant.wishes}\n\n"
                    
                    message_text += "🎁 <b>Дата обміну подарунками:</b> 28.12 в ігротеці\n\n"
                    message_text += "💰 <b>Рекомендована вартість:</b> 200-300 грн\n"
                    message_text += "   (за бажанням можна подарувати за більшу вартість)\n\n"
                    message_text += "🎄 Гарного вам святкового настрою!"
                    
                    try:
                        await bot.send_message(
                            chat_id=giver.telegram_id,
                            text=message_text,
                            parse_mode="HTML"
                        )
                        success_count += 1
                    except Exception as e:
                        logger.error(f"Помилка відправки повідомлення користувачу {giver.telegram_id}: {e}")
            
            await bot.session.close()
            
            # Очищаємо збережені результати
            del draw_results[user_id]
            
            # Повідомляємо адміна про успіх
            await callback.message.edit_text(
                f"✅ <b>Готово!</b>\n\n"
                f"Повідомлення відправлено: {success_count} з {len(pairs)} учасників\n\n"
                f"Жеребкування завершено! Учасники отримали інформацію про своїх підопічних.",
                parse_mode="HTML"
            )
            await callback.answer("✅ Повідомлення розіслано!")
            
        except Exception as e:
            logger.error(f"Помилка при розсилці повідомлень: {e}")
            await callback.answer(f"❌ Помилка: {e}", show_alert=True)


def conduct_draw(participants):
    """
    Проводить жеребкування - випадковий розподіл учасників
    Повертає список пар (giver_id, receiver_id)
    """
    # Створюємо список ID учасників
    user_ids = [p.user_id for p in participants]
    
    # Створюємо копію для призначень
    receivers = user_ids.copy()
    
    # Перемішуємо отримувачів
    random.shuffle(receivers)
    
    # Якщо хтось отримав сам себе, міняємо місцями
    for i in range(len(user_ids)):
        if user_ids[i] == receivers[i]:
            # Знаходимо когось іншого для обміну
            swap_idx = (i + 1) % len(user_ids)
            receivers[i], receivers[swap_idx] = receivers[swap_idx], receivers[i]
    
    # Формуємо пари
    pairs = [(user_ids[i], receivers[i]) for i in range(len(user_ids))]
    
    return pairs


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

