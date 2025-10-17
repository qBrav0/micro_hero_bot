from datetime import date, timedelta
from typing import List, Dict, Optional, Union
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import GameSession, Event
from database.crud import (
    get_upcoming_sessions, get_upcoming_events,
    get_game_sessions, get_events_by_period
)
from utils.helpers import format_date, format_time


class CombinedScheduleService:
    """Сервіс для роботи з об'єднаним розкладом (ігри + події)"""
    
    @staticmethod
    async def get_all_upcoming_schedule(session: AsyncSession, days: int = 30) -> Dict[date, List[Union[GameSession, Event]]]:
        """Отримати об'єднаний розклад ігор та подій на найближчі N днів"""
        # Отримуємо ігри та події окремо
        game_sessions = await get_upcoming_sessions(session, days=days)
        events = await get_upcoming_events(session, days=days)
        
        # Об'єднуємо в один словник по датах
        combined = {}
        
        # Додаємо ігри
        for game_session in game_sessions:
            if game_session.date not in combined:
                combined[game_session.date] = []
            combined[game_session.date].append(game_session)
        
        # Додаємо події
        for event in events:
            if event.date not in combined:
                combined[event.date] = []
            combined[event.date].append(event)
        
        # Сортуємо по датах
        return dict(sorted(combined.items()))
    
    @staticmethod
    async def get_schedule_by_period(
        session: AsyncSession,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> Dict[date, List[Union[GameSession, Event]]]:
        """Отримати об'єднаний розклад за період"""
        # Отримуємо ігри та події окремо
        game_sessions = await get_game_sessions(session, from_date=from_date, to_date=to_date)
        events = await get_events_by_period(session, from_date=from_date, to_date=to_date)
        
        # Об'єднуємо в один словник по датах
        combined = {}
        
        # Додаємо ігри
        for game_session in game_sessions:
            if game_session.date not in combined:
                combined[game_session.date] = []
            combined[game_session.date].append(game_session)
        
        # Додаємо події
        for event in events:
            if event.date not in combined:
                combined[event.date] = []
            combined[event.date].append(event)
        
        # Сортуємо по датах
        return dict(sorted(combined.items()))
    
    @staticmethod
    async def get_schedule_for_date(session: AsyncSession, target_date: date) -> List[Union[GameSession, Event]]:
        """Отримати розклад на конкретну дату"""
        combined = await CombinedScheduleService.get_schedule_by_period(
            session, from_date=target_date, to_date=target_date
        )
        return combined.get(target_date, [])
    
    @staticmethod
    def is_game_session(item: Union[GameSession, Event]) -> bool:
        """Перевірити, чи є елемент ігровою сесією"""
        return hasattr(item, 'game_id')
    
    @staticmethod
    def is_event(item: Union[GameSession, Event]) -> bool:
        """Перевірити, чи є елемент подією"""
        return hasattr(item, 'title')
    
    @staticmethod
    async def format_combined_schedule(
        session: AsyncSession,
        combined_schedule: Dict[date, List[Union[GameSession, Event]]]
    ) -> str:
        """Форматувати об'єднаний розклад"""
        if not combined_schedule:
            return "📅 На найближчі дні немає запланованих ігор та подій.\n\nСлідкуйте за оновленнями!"
        
        text = "📅 <b>Розклад ігор та подій:</b>\n\n"
        
        for schedule_date, items in combined_schedule.items():
            text += f"<b>{format_date(schedule_date)}</b>\n"
            
            # Сортуємо елементи по часу
            sorted_items = sorted(items, key=lambda x: x.start_time)
            
            for item in sorted_items:
                if CombinedScheduleService.is_game_session(item):
                    # Це ігрова сесія
                    from database.crud import get_game, get_registrations
                    game = await get_game(session, item.game_id)
                    if not game or not game.is_active:
                        continue
                    
                    registrations = await get_registrations(session, item.id, active_only=True)
                    players_count = len(registrations)
                    
                    # Додаємо іконку типу оплати
                    payment_icon = {
                        "included": "✅",
                        "free": "🎁",
                        "donate": "💝"
                    }
                    
                    text += f"  {payment_icon.get(item.payment_type, '✅')} <b>{game.name}</b>\n"
                    text += f"     ⏰ {format_time(item.start_time)} - {format_time(item.end_time)}\n"
                    text += f"     👥 {players_count}/{game.max_players}\n\n"
                
                elif CombinedScheduleService.is_event(item):
                    # Це подія
                    from database.crud import get_event_registrations
                    registrations = await get_event_registrations(session, item.id, active_only=True)
                    participants_count = len(registrations)
                    
                    # Додаємо іконку типу оплати
                    payment_icon = {
                        "included": "✅",
                        "free": "🎁",
                        "donate": "💝"
                    }
                    
                    text += f"  {payment_icon.get(item.payment_type, '✅')} <b>🎪 {item.title}</b>\n"
                    text += f"     ⏰ {format_time(item.start_time)} - {format_time(item.end_time)}\n"
                    text += f"     👥 {participants_count}/{item.max_participants}\n\n"
        
        return text
    
    @staticmethod
    async def format_date_schedule(
        session: AsyncSession,
        items: List[Union[GameSession, Event]],
        target_date: date
    ) -> str:
        """Форматувати розклад на конкретну дату"""
        if not items:
            return f"📅 На {format_date(target_date)} немає запланованих ігор та подій."
        
        text = f"📅 <b>{format_date(target_date)}</b>\n\n"
        
        # Сортуємо елементи по часу
        sorted_items = sorted(items, key=lambda x: x.start_time)
        
        games_found = False
        events_found = False
        
        for item in sorted_items:
            if CombinedScheduleService.is_game_session(item):
                # Це ігрова сесія
                from database.crud import get_game, get_registrations
                game = await get_game(session, item.game_id)
                if not game or not game.is_active:
                    continue
                
                if not games_found:
                    text += "<b>🎮 Ігрові сесії:</b>\n"
                    games_found = True
                
                registrations = await get_registrations(session, item.id, active_only=True)
                players_count = len(registrations)
                
                # Додаємо іконку типу оплати
                payment_icon = {
                    "included": "✅",
                    "free": "🎁",
                    "donate": "💝"
                }
                
                text += f"{payment_icon.get(item.payment_type, '✅')} <b>{game.name}</b>\n"
                text += f"   ⏰ {format_time(item.start_time)} - {format_time(item.end_time)}\n"
                text += f"   👥 {players_count}/{game.max_players}\n\n"
            
            elif CombinedScheduleService.is_event(item):
                # Це подія
                from database.crud import get_event_registrations
                registrations = await get_event_registrations(session, item.id, active_only=True)
                participants_count = len(registrations)
                
                if not events_found:
                    text += "<b>🎪 Події:</b>\n"
                    events_found = True
                
                # Додаємо іконку типу оплати
                payment_icon = {
                    "included": "✅",
                    "free": "🎁",
                    "donate": "💝"
                }
                
                text += f"{payment_icon.get(item.payment_type, '✅')} <b>{item.title}</b>\n"
                text += f"   ⏰ {format_time(item.start_time)} - {format_time(item.end_time)}\n"
                text += f"   👥 {participants_count}/{item.max_participants}\n\n"
        
        return text
