from datetime import date, time, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import GameSession, Game
from database.crud import (
    create_game_session, get_game_sessions,
    get_upcoming_sessions, delete_game_session,
    get_game, get_registrations
)
from utils.helpers import format_date, format_time


class ScheduleService:
    """Сервіс для роботи з розкладом"""
    
    @staticmethod
    async def create_session(
        session: AsyncSession,
        game_id: int,
        date: date,
        start_time: str,
        end_time: str,
        created_by: int
    ) -> GameSession:
        """Створити нову сесію гри"""
        return await create_game_session(
            session=session,
            game_id=game_id,
            date=date,
            start_time=start_time,
            end_time=end_time,
            created_by=created_by
        )
    
    @staticmethod
    async def get_upcoming_schedule(session: AsyncSession, days: int = 7) -> List[GameSession]:
        """Отримати розклад на найближчі N днів"""
        return await get_upcoming_sessions(session, days=days)
    
    @staticmethod
    async def get_sessions_by_period(
        session: AsyncSession,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[GameSession]:
        """Отримати сесії за період"""
        return await get_game_sessions(session, from_date=from_date, to_date=to_date)
    
    @staticmethod
    async def delete_session(session: AsyncSession, session_id: int) -> bool:
        """Видалити сесію"""
        return await delete_game_session(session, session_id)
    
    @staticmethod
    async def group_sessions_by_date(sessions: List[GameSession]) -> Dict[date, List[GameSession]]:
        """Згрупувати сесії по датах"""
        grouped = {}
        for game_session in sessions:
            if game_session.date not in grouped:
                grouped[game_session.date] = []
            grouped[game_session.date].append(game_session)
        
        return dict(sorted(grouped.items()))
    
    @staticmethod
    async def format_session_info(
        db_session: AsyncSession,
        game_session: GameSession,
        include_players: bool = False
    ) -> str:
        """Форматувати інформацію про сесію"""
        # Отримуємо гру
        game = await get_game(db_session, game_session.game_id)
        if not game:
            return "❌ Гру не знайдено"
        
        # Отримуємо реєстрації
        registrations = await get_registrations(db_session, game_session.id, active_only=True)
        players_count = len(registrations)
        
        info = f"🎮 <b>{game.name}</b>\n"
        info += f"📅 {format_date(game_session.date)}\n"
        info += f"⏰ {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n"
        info += f"👥 Гравців: {players_count}/{game.max_players}\n"
        
        if include_players and registrations:
            info += f"\n<b>Список гравців:</b>\n"
            # TODO: Отримати інформацію про користувачів
        
        return info
    
    @staticmethod
    async def format_schedule(
        db_session: AsyncSession,
        sessions: List[GameSession]
    ) -> str:
        """Форматувати весь розклад"""
        if not sessions:
            return "📅 На найближчі дні немає запланованих ігор.\n\nСлідкуйте за оновленнями!"
        
        grouped = await ScheduleService.group_sessions_by_date(sessions)
        
        text = "📅 <b>Розклад ігор:</b>\n\n"
        
        for session_date, date_sessions in grouped.items():
            text += f"<b>{format_date(session_date)}</b>\n"
            
            for game_session in date_sessions:
                game = await get_game(db_session, game_session.game_id)
                if not game:
                    continue
                
                registrations = await get_registrations(db_session, game_session.id, active_only=True)
                players_count = len(registrations)
                
                text += f"  🎮 {game.name}\n"
                text += f"     ⏰ {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n"
                text += f"     👥 {players_count}/{game.max_players}\n\n"
        
        return text
