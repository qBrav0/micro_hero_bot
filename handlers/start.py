from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from sqlalchemy.ext.asyncio import AsyncSession
from database import get_session, get_user_by_telegram_id, create_user
from keyboards import get_main_menu
from config import ADMIN_IDS, CLUB_NAME, CLUB_DESCRIPTION

router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message):
    """Обробник команди /start"""
    user_id = message.from_user.id
    
    # Отримуємо сесію БД
    async for session in get_session():
        # Перевіряємо, чи існує користувач
        user = await get_user_by_telegram_id(session, user_id)
        
        is_admin = user_id in ADMIN_IDS
        
        if not user:
            # Створюємо нового користувача
            await create_user(
                session=session,
                telegram_id=user_id,
                username=message.from_user.username,
                first_name=message.from_user.first_name,
                last_name=message.from_user.last_name,
                is_admin=is_admin
            )
        
        welcome_text = f"👋 Вітаємо в <b>{CLUB_NAME}</b>!\n\n"
        welcome_text += f"{CLUB_DESCRIPTION}\n\n"
        welcome_text += "Оберіть дію з меню нижче:"
        
        await message.answer(
            welcome_text,
            reply_markup=get_main_menu(is_admin=is_admin),
            parse_mode="HTML"
        )


@router.message(Command("help"))
async def cmd_help(message: Message):
    """Обробник команди /help"""
    help_text = "ℹ️ <b>Довідка</b>\n\n"
    help_text += "<b>Доступні команди:</b>\n"
    help_text += "/start - Почати роботу з ботом\n"
    help_text += "/help - Показати цю довідку\n\n"
    help_text += "<b>Основні функції:</b>\n"
    help_text += "📅 Розклад ігор - переглянути майбутні ігри\n"
    help_text += "🎮 Мої записи - переглянути ваші активні реєстрації\n"
    help_text += "ℹ️ Про ігротеку - інформація про клуб\n"
    
    await message.answer(help_text, parse_mode="HTML")
