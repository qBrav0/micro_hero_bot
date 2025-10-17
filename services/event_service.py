from datetime import date, time, timedelta
from typing import List, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import Event, EventRegistration
from database.crud import (
    create_event, get_all_events, get_upcoming_events,
    get_events_by_period, delete_event, get_event,
    get_event_registrations, create_event_registration,
    cancel_event_registration, check_user_registered_for_event,
    get_user_event_registrations, update_event
)
from utils.helpers import format_date, format_time


class EventService:
    """Сервіс для роботи з подіями"""
    
    @staticmethod
    async def create_new_event(
        session: AsyncSession,
        title: str,
        description: str,
        min_participants: int,
        max_participants: int,
        date: date,
        start_time: str,
        end_time: str,
        payment_type: str,
        created_by: int,
        image_file_id: Optional[str] = None
    ) -> Event:
        """Створити нову подію"""
        return await create_event(
            session=session,
            title=title,
            description=description,
            min_participants=min_participants,
            max_participants=max_participants,
            date=date,
            start_time=start_time,
            end_time=end_time,
            payment_type=payment_type,
            created_by=created_by,
            image_file_id=image_file_id
        )
    
    @staticmethod
    async def get_upcoming_schedule(session: AsyncSession, days: int = 7) -> List[Event]:
        """Отримати розклад подій на найближчі N днів"""
        return await get_upcoming_events(session, days=days)
    
    @staticmethod
    async def get_events_by_period(
        session: AsyncSession,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None
    ) -> List[Event]:
        """Отримати події за період"""
        return await get_events_by_period(session, from_date=from_date, to_date=to_date)
    
    @staticmethod
    async def delete_event(session: AsyncSession, event_id: int) -> bool:
        """Видалити подію"""
        return await delete_event(session, event_id)
    
    @staticmethod
    async def get_event_by_id(session: AsyncSession, event_id: int) -> Optional[Event]:
        """Отримати подію за ID"""
        return await get_event(session, event_id)
    
    @staticmethod
    async def get_all_active_events(session: AsyncSession) -> List[Event]:
        """Отримати всі активні події"""
        return await get_all_events(session, active_only=True)
    
    @staticmethod
    async def group_events_by_date(events: List[Event]) -> Dict[date, List[Event]]:
        """Згрупувати події по датах"""
        grouped = {}
        for event in events:
            if event.date not in grouped:
                grouped[event.date] = []
            grouped[event.date].append(event)
        
        return dict(sorted(grouped.items()))
    
    @staticmethod
    async def format_event_info(
        db_session: AsyncSession,
        event: Event,
        include_participants: bool = False
    ) -> str:
        """Форматувати інформацію про подію"""
        # Отримуємо реєстрації
        registrations = await get_event_registrations(db_session, event.id, active_only=True)
        participants_count = len(registrations)
        
        info = f"🎪 <b>{event.title}</b>\n"
        info += f"📅 {format_date(event.date)}\n"
        info += f"⏰ {format_time(event.start_time)} - {format_time(event.end_time)}\n"
        info += f"👥 Учасників: {participants_count}/{event.max_participants}\n"
        
        if include_participants and registrations:
            info += f"\n<b>Список учасників:</b>\n"
            # TODO: Отримати інформацію про користувачів
        
        return info
    
    @staticmethod
    async def format_events_schedule(
        db_session: AsyncSession,
        events: List[Event]
    ) -> str:
        """Форматувати весь розклад подій"""
        if not events:
            return "📅 На найближчі дні немає запланованих подій.\n\nСлідкуйте за оновленнями!"
        
        grouped = await EventService.group_events_by_date(events)
        
        text = "🎪 <b>Розклад подій:</b>\n\n"
        
        for event_date, date_events in grouped.items():
            text += f"<b>{format_date(event_date)}</b>\n"
            
            for event in date_events:
                registrations = await get_event_registrations(db_session, event.id, active_only=True)
                participants_count = len(registrations)
                
                text += f"  🎪 {event.title}\n"
                text += f"     ⏰ {format_time(event.start_time)} - {format_time(event.end_time)}\n"
                text += f"     👥 {participants_count}/{event.max_participants}\n\n"
        
        return text
    
    @staticmethod
    async def register_user_for_event(
        session: AsyncSession,
        user_id: int,
        event_id: int
    ) -> bool:
        """Зареєструвати користувача на подію"""
        # Перевіряємо чи вже зареєстрований
        if await check_user_registered_for_event(session, user_id, event_id):
            return False
        
        # Перевіряємо чи є місця
        event = await get_event(session, event_id)
        if not event:
            return False
        
        registrations = await get_event_registrations(session, event_id, active_only=True)
        if len(registrations) >= event.max_participants:
            return False
        
        # Створюємо реєстрацію
        await create_event_registration(session, user_id, event_id)
        return True
    
    @staticmethod
    async def cancel_user_registration(
        session: AsyncSession,
        user_id: int,
        event_id: int
    ) -> bool:
        """Скасувати реєстрацію користувача на подію"""
        return await cancel_event_registration(session, user_id, event_id)
    
    @staticmethod
    async def get_user_registrations(
        session: AsyncSession,
        user_id: int
    ) -> List[EventRegistration]:
        """Отримати реєстрації користувача на події"""
        return await get_user_event_registrations(session, user_id, active_only=True)
    
    @staticmethod
    async def update_event_info(
        session: AsyncSession,
        event: Event,
        title: Optional[str] = None,
        description: Optional[str] = None,
        min_participants: Optional[int] = None,
        max_participants: Optional[int] = None,
        date: Optional[date] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        payment_type: Optional[str] = None,
        image_file_id: Optional[str] = None
    ) -> Event:
        """Оновити інформацію про подію"""
        if title is not None:
            event.title = title
        if description is not None:
            event.description = description
        if min_participants is not None:
            event.min_participants = min_participants
        if max_participants is not None:
            event.max_participants = max_participants
        if date is not None:
            event.date = date
        if start_time is not None:
            event.start_time = start_time
        if end_time is not None:
            event.end_time = end_time
        if payment_type is not None:
            event.payment_type = payment_type
        if image_file_id is not None:
            event.image_file_id = image_file_id
        
        return await update_event(session, event)
    
    @staticmethod
    def format_event_info_for_list(event: Event) -> str:
        """Форматувати інформацію про подію для списку"""
        return f"🎪 <b>{event.title}</b>\n" \
               f"📅 {format_date(event.date)} | ⏰ {format_time(event.start_time)} - {format_time(event.end_time)}\n" \
               f"👥 {event.min_participants}-{event.max_participants} учасників"
