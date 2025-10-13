from aiogram import Router, F
from aiogram.types import Message
from keyboards import get_main_menu
from config import ADMIN_IDS, CLUB_NAME, CLUB_DESCRIPTION

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
    from config import CLUB_ABOUT_TEXT
    
    if CLUB_ABOUT_TEXT:
        # Використовуємо кастомний текст
        about_text = CLUB_ABOUT_TEXT
    else:
        # Використовуємо стандартний текст
        about_text = f"ℹ️ <b>{CLUB_NAME}</b>\n\n"
        about_text += f"{CLUB_DESCRIPTION}\n\n"
        about_text += "🎲 У нас ви можете:\n"
        about_text += "• Грати в настільні ігри\n"
        about_text += "• Знайомитися з новими людьми\n"
        about_text += "• Відкривати для себе нові ігри\n"
        about_text += "• Весело проводити час\n\n"
        about_text += "📅 Слідкуйте за розкладом і записуйтесь на ігри через бота!"
    
    await message.answer(about_text, parse_mode="HTML")


@router.message(F.text == "🏆 Топ-10 ігротеки")
async def show_top_players(message: Message):
    """Показати топ-10 гравців за кількістю відвіданих сесій"""
    from database import get_session, get_top_users_by_attended_sessions
    
    async for session in get_session():
        top_users = await get_top_users_by_attended_sessions(session, limit=10)
        
        if not top_users:
            await message.answer(
                "🏆 <b>Топ-10 ігротеки</b>\n\n"
                "Поки що немає статистики відвідування сесій.\n\n"
                "Записуйтесь на ігри та відвідуйте їх, щоб потрапити в топ!",
                parse_mode="HTML"
            )
            return
        
        text = "🏆 <b>Топ-10 ігротеки</b>\n\n"
        text += "Найактивніші гравці за кількістю відвіданих ігрових сесій:\n\n"
        
        medals = ["🥇", "🥈", "🥉"]
        
        for i, user_data in enumerate(top_users, 1):
            # user_data має атрибути: id, telegram_id, username, first_name, last_name, sessions_count
            medal = medals[i-1] if i <= 3 else f"{i}."
            
            name = user_data.first_name
            if user_data.last_name:
                name += f" {user_data.last_name}"
            
            username_str = f"@{user_data.username}" if user_data.username else name
            sessions_count = user_data.sessions_count
            
            text += f"{medal} <b>{username_str}</b> — {sessions_count} сесій\n"
        
        text += "\n💡 Відвідуйте більше ігор, щоб потрапити в топ!"
        
        await message.answer(text, parse_mode="HTML")


@router.message(F.text == "💳 Оплата")
async def show_payment_info(message: Message):
    """Показати інформацію про оплату"""
    from config import PAYMENT_INFO, PAYMENT_CARD_NUMBER, PAYMENT_BANK_LINK
    
    if PAYMENT_INFO:
        # Використовуємо кастомну інформацію
        text = PAYMENT_INFO
    else:
        # Використовуємо стандартну інформацію
        text = "💳 <b>Інформація про оплату</b>\n\n"
        text += "📋 <b>Як це працює:</b>\n"
        text += "• При створенні розкладу адміністратор вказує ціну входу на день\n"
        text += "• Ціна відрізняється для дорослих та дітей до 18 років включно\n"
        text += "• Деякі ігрові сесії можуть бути безкоштовними або за вільну ціну (donate)\n\n"
        
        if PAYMENT_CARD_NUMBER:
            text += f"💳 <b>Номер картки:</b>\n<code>{PAYMENT_CARD_NUMBER}</code>\n\n"
        
        if PAYMENT_BANK_LINK:
            text += f"🔗 <b>Посилання на банку:</b>\n{PAYMENT_BANK_LINK}\n\n"
        
        text += "ℹ️ При реєстрації на гру ви побачите вартість входу та умови оплати для кожної сесії."
    
    await message.answer(text, parse_mode="HTML")
