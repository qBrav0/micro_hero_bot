from typing import List, Dict
from datetime import datetime, timedelta, date, time as dt_time
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select
from collections import defaultdict

from database.models import User, Registration, GameSession, Game, ReminderSent, EventRegistration, Event, EventReminderSent
from database.crud import get_game, get_event
from utils.helpers import format_date, format_time
import logging

logger = logging.getLogger(__name__)


class ReminderService:
    """Сервіс для відправки нагадувань про записи"""
    
    @staticmethod
    async def send_reminders(bot: Bot, db_session: AsyncSession):
        """
        Перевірити та відправити нагадування користувачам
        
        Логіка:
        1. Знаходимо всіх користувачів з увімкненими нагадуваннями
        2. Для кожного користувача знаходимо його активні записи
        3. Групуємо записи по датах
        4. Для кожної дати знаходимо найранішу сесію
        5. Якщо час нагадування настав (зараз = start_time - reminder_hours), відправляємо нагадування
        """
        try:
            # Отримуємо користувачів з увімкненими нагадуваннями
            result = await db_session.execute(
                select(User).where(
                    User.reminder_enabled == True,
                    User.reminder_hours_before != None
                )
            )
            users_with_reminders = result.scalars().all()
            
            if not users_with_reminders:
                logger.debug("Немає користувачів з увімкненими нагадуваннями")
                return
            
            logger.info(f"Знайдено {len(users_with_reminders)} користувачів з увімкненими нагадуваннями")
            
            now = datetime.now()
            current_date = now.date()
            current_time = now.time()
            
            for user in users_with_reminders:
                try:
                    # Перевіряємо нагадування для ігор
                    await ReminderService._check_and_send_user_reminders(
                        bot, db_session, user, now, current_date, current_time
                    )
                    
                    # Перевіряємо нагадування для подій
                    await ReminderService._check_and_send_user_event_reminders(
                        bot, db_session, user, now, current_date, current_time
                    )
                except Exception as e:
                    logger.error(f"Помилка при обробці нагадувань для користувача {user.telegram_id}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Помилка в send_reminders: {e}")
    
    @staticmethod
    async def _check_reminder_sent(db_session: AsyncSession, user_id: int, session_date: date) -> bool:
        """Перевірити чи вже було відправлено нагадування для цієї дати"""
        result = await db_session.execute(
            select(ReminderSent).where(
                ReminderSent.user_id == user_id,
                ReminderSent.session_date == session_date
            )
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def _mark_reminder_sent(db_session: AsyncSession, user_id: int, session_date: date):
        """Позначити що нагадування було відправлено"""
        reminder_sent = ReminderSent(
            user_id=user_id,
            session_date=session_date
        )
        db_session.add(reminder_sent)
        await db_session.commit()
    
    @staticmethod
    async def _check_and_send_user_reminders(
        bot: Bot,
        db_session: AsyncSession,
        user: User,
        now: datetime,
        current_date: date,
        current_time: dt_time
    ):
        """Перевірити та відправити нагадування для конкретного користувача"""
        
        # Отримуємо активні реєстрації користувача
        result = await db_session.execute(
            select(Registration).where(
                Registration.user_id == user.id,
                Registration.is_active == True
            )
        )
        registrations = result.scalars().all()
        
        if not registrations:
            return
        
        # Отримуємо інформацію про сесії
        session_ids = [reg.session_id for reg in registrations]
        result = await db_session.execute(
            select(GameSession).where(GameSession.id.in_(session_ids))
        )
        sessions = result.scalars().all()
        
        # Групуємо сесії по датах (тільки майбутні)
        sessions_by_date: Dict[date, List[GameSession]] = defaultdict(list)
        
        for session in sessions:
            # Пропускаємо минулі дати
            if session.date < current_date:
                continue
            
            # Перевіряємо чи гра активна
            game = await get_game(db_session, session.game_id)
            if not game or not game.is_active:
                continue
            
            sessions_by_date[session.date].append(session)
        
        if not sessions_by_date:
            return
        
        # Для кожної дати перевіряємо чи потрібно відправити нагадування
        for session_date, day_sessions in sessions_by_date.items():
            # Знаходимо найранішу сесію дня
            earliest_session = min(day_sessions, key=lambda s: s.start_time)
            
            # Вираховуємо час коли потрібно відправити нагадування
            session_datetime = datetime.combine(session_date, earliest_session.start_time)
            reminder_time = session_datetime - timedelta(hours=user.reminder_hours_before)
            
            # Перевіряємо чи настав час для нагадування
            # Відправляємо якщо зараз >= reminder_time і зараз < reminder_time + 10 хвилин
            # (щоб не відправляти повторно)
            time_diff = (now - reminder_time).total_seconds()
            
            # Відправляємо якщо різниця від 0 до 10 хвилин (600 секунд)
            if 0 <= time_diff <= 600:
                # Перевіряємо чи вже було відправлено нагадування для цієї дати
                reminder_exists = await ReminderService._check_reminder_sent(
                    db_session, user.id, session_date
                )
                
                if not reminder_exists:
                    await ReminderService._send_reminder_message(
                        bot, db_session, user, session_date, day_sessions
                    )
    
    @staticmethod
    async def _send_reminder_message(
        bot: Bot,
        db_session: AsyncSession,
        user: User,
        session_date: date,
        sessions: List[GameSession]
    ):
        """Відправити нагадування користувачу про записи на день"""
        try:
            # Сортуємо сесії за часом початку
            sorted_sessions = sorted(sessions, key=lambda s: s.start_time)
            
            # Формуємо повідомлення
            text = "🔔 <b>Нагадування про записи</b>\n\n"
            text += f"📅 <b>Дата:</b> {format_date(session_date)}\n\n"
            
            if len(sorted_sessions) == 1:
                text += "У вас є запис на гру:\n\n"
            else:
                text += f"У вас є {len(sorted_sessions)} записів на ігри:\n\n"
            
            # Додаємо інформацію про кожну сесію
            for i, game_session in enumerate(sorted_sessions, 1):
                game = await get_game(db_session, game_session.game_id)
                if not game:
                    continue
                
                text += f"{i}. 🎮 <b>{game.name}</b>\n"
                text += f"   ⏰ {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n"
                
                # Додаємо тип оплати
                payment_type_text = {
                    "included": "✅ Входить в оплату",
                    "free": "🎁 Безкоштовна",
                    "donate": "💝 Free donate"
                }
                text += f"   💳 {payment_type_text.get(game_session.payment_type, 'Входить в оплату')}\n\n"
            
            text += "Бажаємо приємної гри! 🎲\n\n"
            text += "💡 Якщо плани змінилися, не забудьте скасувати запис через бота."
            
            # Відправляємо повідомлення
            await bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML"
            )
            
            # Позначаємо що нагадування було відправлено
            await ReminderService._mark_reminder_sent(db_session, user.id, session_date)
            
            logger.info(
                f"Відправлено нагадування користувачу {user.telegram_id} "
                f"про {len(sorted_sessions)} сесій на {session_date}"
            )
            
        except Exception as e:
            logger.error(f"Помилка при відправці нагадування користувачу {user.telegram_id}: {e}")
    
    @staticmethod
    async def _check_event_reminder_sent(db_session: AsyncSession, user_id: int, event_date: date) -> bool:
        """Перевірити чи вже було відправлено нагадування для цієї дати події"""
        result = await db_session.execute(
            select(EventReminderSent).where(
                EventReminderSent.user_id == user_id,
                EventReminderSent.event_date == event_date
            )
        )
        return result.scalar_one_or_none() is not None
    
    @staticmethod
    async def _mark_event_reminder_sent(db_session: AsyncSession, user_id: int, event_date: date):
        """Позначити що нагадування про подію було відправлено"""
        reminder_sent = EventReminderSent(
            user_id=user_id,
            event_date=event_date
        )
        db_session.add(reminder_sent)
        await db_session.commit()
    
    @staticmethod
    async def _check_and_send_user_event_reminders(
        bot: Bot,
        db_session: AsyncSession,
        user: User,
        now: datetime,
        current_date: date,
        current_time: dt_time
    ):
        """Перевірити та відправити нагадування для подій конкретного користувача"""
        
        # Отримуємо активні реєстрації користувача на події
        result = await db_session.execute(
            select(EventRegistration).where(
                EventRegistration.user_id == user.id,
                EventRegistration.is_active == True
            )
        )
        event_registrations = result.scalars().all()
        
        if not event_registrations:
            return
        
        # Отримуємо інформацію про події
        event_ids = [reg.event_id for reg in event_registrations]
        result = await db_session.execute(
            select(Event).where(Event.id.in_(event_ids))
        )
        events = result.scalars().all()
        
        # Групуємо події по датах (тільки майбутні)
        events_by_date: Dict[date, List[Event]] = defaultdict(list)
        
        for event in events:
            # Пропускаємо минулі дати
            if event.date < current_date:
                continue
            
            events_by_date[event.date].append(event)
        
        if not events_by_date:
            return
        
        # Для кожної дати перевіряємо чи потрібно відправити нагадування
        for event_date, day_events in events_by_date.items():
            # Знаходимо найранішу подію дня
            earliest_event = min(day_events, key=lambda e: e.start_time)
            
            # Вираховуємо час коли потрібно відправити нагадування
            event_datetime = datetime.combine(event_date, earliest_event.start_time)
            reminder_time = event_datetime - timedelta(hours=user.reminder_hours_before)
            
            # Перевіряємо чи настав час для нагадування
            # Відправляємо якщо зараз >= reminder_time і зараз < reminder_time + 10 хвилин
            # (щоб не відправляти повторно)
            time_diff = (now - reminder_time).total_seconds()
            
            # Відправляємо якщо різниця від 0 до 10 хвилин (600 секунд)
            if 0 <= time_diff <= 600:
                # Перевіряємо чи вже було відправлено нагадування для цієї дати
                reminder_exists = await ReminderService._check_event_reminder_sent(
                    db_session, user.id, event_date
                )
                
                if not reminder_exists:
                    await ReminderService._send_event_reminder_message(
                        bot, db_session, user, event_date, day_events
                    )
    
    @staticmethod
    async def _send_event_reminder_message(
        bot: Bot,
        db_session: AsyncSession,
        user: User,
        event_date: date,
        events: List[Event]
    ):
        """Відправити нагадування користувачу про події на день"""
        try:
            # Сортуємо події за часом початку
            sorted_events = sorted(events, key=lambda e: e.start_time)
            
            # Формуємо повідомлення
            text = "🔔 <b>Нагадування про події</b>\n\n"
            text += f"📅 <b>Дата:</b> {format_date(event_date)}\n\n"
            
            if len(sorted_events) == 1:
                text += "У вас є реєстрація на подію:\n\n"
            else:
                text += f"У вас є {len(sorted_events)} реєстрацій на події:\n\n"
            
            # Додаємо інформацію про кожну подію
            for i, event in enumerate(sorted_events, 1):
                text += f"{i}. 🎪 <b>{event.title}</b>\n"
                text += f"   ⏰ {format_time(event.start_time)} - {format_time(event.end_time)}\n"
                
                # Додаємо тип оплати
                payment_type_text = {
                    "included": "✅ Входить в оплату",
                    "free": "🎁 Безкоштовна",
                    "donate": "💝 Free donate"
                }
                text += f"   💳 {payment_type_text.get(event.payment_type, 'Входить в оплату')}\n\n"
            
            text += "Бажаємо приємно провести час! 🎪\n\n"
            text += "💡 Якщо плани змінилися, не забудьте скасувати реєстрацію через бота."
            
            # Відправляємо повідомлення
            await bot.send_message(
                chat_id=user.telegram_id,
                text=text,
                parse_mode="HTML"
            )
            
            # Позначаємо що нагадування було відправлено
            await ReminderService._mark_event_reminder_sent(db_session, user.id, event_date)
            
            logger.info(
                f"Відправлено нагадування про події користувачу {user.telegram_id} "
                f"про {len(sorted_events)} подій на {event_date}"
            )
            
        except Exception as e:
            logger.error(f"Помилка при відправці нагадування про події користувачу {user.telegram_id}: {e}")

