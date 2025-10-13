from typing import List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Registration, GameSession, Game, User
from database.crud import (
    create_registration, get_registrations,
    cancel_registration, get_user_registrations,
    check_user_registered, get_game, get_game_sessions
)


class RegistrationService:
    """Сервіс для роботи з реєстраціями"""
    
    @staticmethod
    async def register_user(
        session: AsyncSession,
        user_id: int,
        session_id: int
    ) -> Tuple[bool, str]:
        """
        Зареєструвати користувача на гру
        Повертає: (успішно, повідомлення)
        """
        # Перевіряємо, чи користувач вже зареєстрований
        is_registered = await check_user_registered(session, user_id, session_id)
        if is_registered:
            return False, "⚠️ Ви вже зареєстровані на цю гру!"
        
        # Отримуємо сесію гри
        from sqlmodel import select
        result = await session.execute(
            select(GameSession).where(GameSession.id == session_id)
        )
        game_session = result.scalar_one_or_none()
        
        if not game_session:
            return False, "❌ Сесію не знайдено!"
        
        # Отримуємо гру
        game = await get_game(session, game_session.game_id)
        if not game:
            return False, "❌ Гру не знайдено!"
        
        # Перевіряємо кількість місць
        registrations = await get_registrations(session, session_id, active_only=True)
        if len(registrations) >= game.max_players:
            return False, f"⚠️ На цю гру вже немає вільних місць!\n\nЗареєстровано: {len(registrations)}/{game.max_players}"
        
        # Реєструємо користувача
        await create_registration(session, user_id, session_id)
        
        return True, "✅ Ви успішно зареєструвалися на гру!"
    
    @staticmethod
    async def unregister_user(
        session: AsyncSession,
        user_id: int,
        session_id: int
    ) -> Tuple[bool, str]:
        """
        Скасувати реєстрацію користувача
        Повертає: (успішно, повідомлення)
        """
        success = await cancel_registration(session, user_id, session_id)
        
        if success:
            return True, "✅ Реєстрацію скасовано!"
        else:
            return False, "⚠️ Ви не зареєстровані на цю гру!"
    
    @staticmethod
    async def get_user_active_registrations(
        session: AsyncSession,
        user_id: int
    ) -> List[Registration]:
        """Отримати активні реєстрації користувача"""
        return await get_user_registrations(session, user_id, active_only=True)
    
    @staticmethod
    async def get_session_registrations(
        session: AsyncSession,
        session_id: int
    ) -> List[Registration]:
        """Отримати реєстрації для сесії"""
        return await get_registrations(session, session_id, active_only=True)
    
    @staticmethod
    async def is_user_registered(
        session: AsyncSession,
        user_id: int,
        session_id: int
    ) -> bool:
        """Перевірити, чи зареєстрований користувач"""
        return await check_user_registered(session, user_id, session_id)
    
    @staticmethod
    async def format_registrations_list(
        db_session: AsyncSession,
        registrations: List[Registration]
    ) -> str:
        """Форматувати список реєстрацій (тільки майбутні сесії)"""
        from sqlmodel import select
        from utils.helpers import format_date, format_time
        from datetime import date
        
        today = date.today()
        future_registrations = []
        
        # Фільтруємо тільки майбутні сесії
        for reg in registrations:
            result = await db_session.execute(
                select(GameSession).where(GameSession.id == reg.session_id)
            )
            game_session = result.scalar_one_or_none()
            
            if game_session and game_session.date >= today:
                future_registrations.append((reg, game_session))
        
        if not future_registrations:
            return "📋 У вас немає активних записів.\n\nОберіть гру з розкладу, щоб записатися!"
        
        text = "🎮 <b>Ваші записи:</b>\n\n"
        
        for i, (reg, game_session) in enumerate(future_registrations, 1):
            # Отримуємо гру
            game = await get_game(db_session, game_session.game_id)
            if not game:
                continue
            
            text += f"{i}. 🎮 <b>{game.name}</b>\n"
            text += f"   📅 {format_date(game_session.date)}\n"
            text += f"   ⏰ {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n\n"
        
        return text
