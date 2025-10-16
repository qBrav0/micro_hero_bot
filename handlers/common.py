from aiogram import Router, F
from aiogram.types import Message
from keyboards import get_main_menu
from config import ADMIN_IDS

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


@router.message(F.text == "🎲 База ігор")
async def show_game_database(message: Message):
    """Показати базу ігор (поки що в розробці)"""
    import random
    
    fun_messages = [
        "🎮 Тестуємо volume! База ігор зараз перевіряє Railway Persistent Storage! 🔧\n\nПоки що знайдіть ігри в розкладі! 🔍",
        "🎲 Debug режим! Кнопка тестує збереження файлів! 🐛\n\nАле не сумуйте - всі ігри вже чекають на вас в розкладі! 📅",
        "🎯 Volume тест! База ігор перевіряє, чи працює постійне сховище! 💾\n\nА поки що - дивіться розклад! 📋",
        "🎪 Тестування! База ігор репетирує збереження імейджів! 🖼️\n\nКоли навчиться, обов'язково покаже! А поки що - розклад в дії! 🎭",
        "🎨 Debug mode! База ігор малює тест для Railway Volume! 🎨\n\nСкоро буде працювати ідеально! А поки що - розклад працює! ✨"
    ]
    
    chosen_message = random.choice(fun_messages)
    await message.answer(chosen_message)


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
