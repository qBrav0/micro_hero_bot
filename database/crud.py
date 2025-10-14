from datetime import date, datetime
from typing import Optional, List
from sqlmodel import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import and_, or_

from .models import User, Game, GameSession, Registration, DayPricing, ClubSettings


# ===== USER CRUD =====

async def create_user(session: AsyncSession, telegram_id: int, username: Optional[str], 
                     first_name: str, last_name: Optional[str], is_admin: bool = False) -> User:
    """Створити нового користувача"""
    user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name,
        last_name=last_name,
        is_admin=is_admin
    )
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


async def get_user_by_telegram_id(session: AsyncSession, telegram_id: int) -> Optional[User]:
    """Отримати користувача за Telegram ID"""
    result = await session.execute(
        select(User).where(User.telegram_id == telegram_id)
    )
    return result.scalar_one_or_none()


async def update_user(session: AsyncSession, user: User) -> User:
    """Оновити користувача"""
    session.add(user)
    await session.commit()
    await session.refresh(user)
    return user


# ===== GAME CRUD =====

async def create_game(session: AsyncSession, name: str, description: str,
                     min_players: int, max_players: int, avg_duration: int,
                     image_path: Optional[str] = None) -> Game:
    """Створити нову гру"""
    game = Game(
        name=name,
        description=description,
        min_players=min_players,
        max_players=max_players,
        avg_duration=avg_duration,
        image_path=image_path
    )
    session.add(game)
    await session.commit()
    await session.refresh(game)
    return game


async def get_game(session: AsyncSession, game_id: int, active_only: bool = True) -> Optional[Game]:
    """Отримати гру за ID"""
    query = select(Game).where(Game.id == game_id)
    if active_only:
        query = query.where(Game.is_active == True)
    
    result = await session.execute(query)
    return result.scalar_one_or_none()


async def get_all_games(session: AsyncSession, active_only: bool = True) -> List[Game]:
    """Отримати всі ігри"""
    query = select(Game)
    if active_only:
        query = query.where(Game.is_active == True)
    result = await session.execute(query)
    return list(result.scalars().all())


async def update_game(session: AsyncSession, game: Game) -> Game:
    """Оновити гру"""
    session.add(game)
    await session.commit()
    await session.refresh(game)
    return game


async def delete_game(session: AsyncSession, game_id: int) -> bool:
    """Видалити гру (м'яке видалення) та всі активні сесії"""
    game = await get_game(session, game_id, active_only=False)  # Отримуємо навіть неактивні ігри
    if game:
        # Спочатку видаляємо всі активні сесії цієї гри
        from sqlmodel import select
        from database.models import GameSession, User, Registration
        from datetime import date
        
        # Знаходимо всі майбутні сесії цієї гри
        result = await session.execute(
            select(GameSession).where(
                GameSession.game_id == game_id,
                GameSession.date >= date.today()
            )
        )
        future_sessions = result.scalars().all()
        
        # Збираємо інформацію про користувачів для сповіщення
        users_to_notify = set()
        sessions_info = []
        
        for game_session in future_sessions:
            # Отримуємо всіх зареєстрованих користувачів на цю сесію
            registrations_result = await session.execute(
                select(Registration, User).join(User, Registration.user_id == User.id).where(
                    Registration.session_id == game_session.id,
                    Registration.is_active == True
                )
            )
            
            session_users = []
            for registration, user in registrations_result:
                users_to_notify.add((user.telegram_id, user.first_name, user.last_name))
                session_users.append(user)
            
            if session_users:  # Тільки якщо є користувачі для сповіщення
                sessions_info.append({
                    'session': game_session,
                    'users': session_users
                })
        
        # Видаляємо кожну сесію (це також видалить реєстрації)
        for game_session in future_sessions:
            await delete_game_session(session, game_session.id)
        
        # Відправляємо сповіщення користувачам
        if sessions_info:
            await _notify_users_about_game_deletion(game, sessions_info)
        
        # Потім позначаємо гру як неактивну
        game.is_active = False
        await update_game(session, game)
        return True
    return False


async def _notify_users_about_game_deletion(game, sessions_info):
    """Відправити сповіщення користувачам про видалення гри"""
    try:
        from aiogram import Bot
        from config import BOT_TOKEN
        from utils.helpers import format_date, format_time
        
        bot = Bot(token=BOT_TOKEN)
        
        for session_data in sessions_info:
            game_session = session_data['session']
            users = session_data['users']
            
            # Формуємо текст сповіщення
            notification_text = f"❌ <b>Сесію гри скасовано</b>\n\n"
            notification_text += f"🎮 Гра: <b>{game.name}</b>\n"
            notification_text += f"📅 Дата: {format_date(game_session.date)}\n"
            notification_text += f"⏰ Час: {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n\n"
            notification_text += "Гра була видалена з ігротеки. Вибачте за незручності.\n"
            notification_text += "Слідкуйте за оновленнями розкладу для нових ігор!"
            
            # Відправляємо кожному користувачу
            for user in users:
                try:
                    await bot.send_message(
                        chat_id=user.telegram_id,
                        text=notification_text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    print(f"Помилка надсилання повідомлення користувачу {user.telegram_id}: {e}")
        
        await bot.session.close()
        
    except Exception as e:
        print(f"Помилка при відправці сповіщень про видалення гри: {e}")


# ===== GAME SESSION CRUD =====

async def create_game_session(session: AsyncSession, game_id: int, date: date,
                              start_time: str, end_time: str, payment_type: str, created_by: int) -> GameSession:
    """Створити сесію гри"""
    from datetime import time as dt_time
    
    # Конвертуємо строки у time об'єкти
    start = dt_time.fromisoformat(start_time)
    end = dt_time.fromisoformat(end_time)
    
    game_session = GameSession(
        game_id=game_id,
        date=date,
        start_time=start,
        end_time=end,
        payment_type=payment_type,
        created_by=created_by
    )
    session.add(game_session)
    await session.commit()
    await session.refresh(game_session)
    return game_session


async def get_game_sessions(session: AsyncSession, from_date: Optional[date] = None,
                           to_date: Optional[date] = None) -> List[GameSession]:
    """Отримати сесії ігор за період (тільки з активних ігор)"""
    query = select(GameSession).join(Game).where(Game.is_active == True)
    
    if from_date:
        query = query.where(GameSession.date >= from_date)
    if to_date:
        query = query.where(GameSession.date <= to_date)
    
    query = query.order_by(GameSession.date, GameSession.start_time)
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_upcoming_sessions(session: AsyncSession, days: int = 7) -> List[GameSession]:
    """Отримати майбутні сесії на найближчі N днів (тільки з активних ігор)"""
    from datetime import date, timedelta
    today = date.today()
    end_date = today + timedelta(days=days)
    
    # Отримуємо сесії з джойном до таблиці Game, щоб фільтрувати тільки активні ігри
    query = select(GameSession).join(Game).where(
        GameSession.date >= today,
        GameSession.date <= end_date,
        Game.is_active == True
    ).order_by(GameSession.date, GameSession.start_time)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def delete_game_session(session: AsyncSession, session_id: int) -> bool:
    """Видалити сесію гри та всі реєстрації на неї"""
    result = await session.execute(
        select(GameSession).where(GameSession.id == session_id)
    )
    game_session = result.scalar_one_or_none()
    
    if game_session:
        # Спочатку видаляємо всі реєстрації на цю сесію (і активні, і неактивні)
        registrations_result = await session.execute(
            select(Registration).where(Registration.session_id == session_id)
        )
        registrations = registrations_result.scalars().all()
        
        for registration in registrations:
            await session.delete(registration)
        
        # Flush для застосування видалення реєстрацій перед видаленням сесії
        await session.flush()
        
        # Тепер видаляємо саму сесію
        await session.delete(game_session)
        await session.commit()
        return True
    return False


# ===== REGISTRATION CRUD =====

async def create_registration(session: AsyncSession, user_id: int, 
                              session_id: int) -> Registration:
    """Створити реєстрацію на гру"""
    registration = Registration(
        user_id=user_id,
        session_id=session_id
    )
    session.add(registration)
    await session.commit()
    await session.refresh(registration)
    return registration


async def get_registrations(session: AsyncSession, session_id: int,
                           active_only: bool = True) -> List[Registration]:
    """Отримати реєстрації для сесії"""
    query = select(Registration).where(Registration.session_id == session_id)
    if active_only:
        query = query.where(Registration.is_active == True)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def get_user_registrations(session: AsyncSession, user_id: int,
                                active_only: bool = True) -> List[Registration]:
    """Отримати реєстрації користувача"""
    query = select(Registration).where(Registration.user_id == user_id)
    if active_only:
        query = query.where(Registration.is_active == True)
    
    result = await session.execute(query)
    return list(result.scalars().all())


async def cancel_registration(session: AsyncSession, user_id: int, 
                              session_id: int) -> bool:
    """Скасувати реєстрацію"""
    result = await session.execute(
        select(Registration).where(
            and_(
                Registration.user_id == user_id,
                Registration.session_id == session_id,
                Registration.is_active == True
            )
        )
    )
    registration = result.scalar_one_or_none()
    
    if registration:
        registration.is_active = False
        session.add(registration)
        await session.commit()
        return True
    return False


async def check_user_registered(session: AsyncSession, user_id: int, 
                                session_id: int) -> bool:
    """Перевірити, чи зареєстрований користувач на сесію"""
    result = await session.execute(
        select(Registration).where(
            and_(
                Registration.user_id == user_id,
                Registration.session_id == session_id,
                Registration.is_active == True
            )
        )
    )
    return result.scalar_one_or_none() is not None


async def get_user_attended_sessions_count(session: AsyncSession, user_id: int) -> int:
    """Отримати кількість сесій які користувач відвідав (минулі сесії де він був записаний)"""
    from datetime import date
    from sqlalchemy import func
    
    today = date.today()
    
    # Підраховуємо кількість активних реєстрацій на минулі сесії
    result = await session.execute(
        select(func.count(Registration.id))
        .join(GameSession, Registration.session_id == GameSession.id)
        .where(
            and_(
                Registration.user_id == user_id,
                Registration.is_active == True,
                GameSession.date < today
            )
        )
    )
    
    return result.scalar() or 0


async def get_top_users_by_attended_sessions(session: AsyncSession, limit: int = 10):
    """Отримати топ користувачів за кількістю відвіданих сесій"""
    from datetime import date
    from sqlalchemy import func
    
    today = date.today()
    
    # Підраховуємо відвідані сесії для кожного користувача
    result = await session.execute(
        select(
            User.id,
            User.telegram_id,
            User.username,
            User.first_name,
            User.last_name,
            func.count(Registration.id).label('sessions_count')
        )
        .join(Registration, User.id == Registration.user_id)
        .join(GameSession, Registration.session_id == GameSession.id)
        .where(
            and_(
                Registration.is_active == True,
                GameSession.date < today
            )
        )
        .group_by(User.id)
        .order_by(func.count(Registration.id).desc())
        .limit(limit)
    )
    
    return result.all()


# ===== DAY PRICING CRUD =====

async def create_day_pricing(session: AsyncSession, date: date, adult_price: int, child_price: int) -> DayPricing:
    """Створити ціноутворення для дня"""
    pricing = DayPricing(
        pricing_date=date,
        adult_price=adult_price,
        child_price=child_price
    )
    session.add(pricing)
    await session.commit()
    await session.refresh(pricing)
    return pricing


async def get_day_pricing(session: AsyncSession, date: date) -> Optional[DayPricing]:
    """Отримати ціноутворення для дня"""
    result = await session.execute(
        select(DayPricing).where(DayPricing.pricing_date == date)
    )
    return result.scalar_one_or_none()


async def update_day_pricing(session: AsyncSession, pricing_id: int, adult_price: int, child_price: int) -> Optional[DayPricing]:
    """Оновити ціноутворення"""
    result = await session.execute(
        select(DayPricing).where(DayPricing.id == pricing_id)
    )
    pricing = result.scalar_one_or_none()
    
    if pricing:
        pricing.adult_price = adult_price
        pricing.child_price = child_price
        await session.commit()
        await session.refresh(pricing)
    
    return pricing


# ===== CLUB SETTINGS CRUD =====

async def get_setting(session: AsyncSession, key: str) -> Optional[str]:
    """Отримати значення налаштування за ключем"""
    result = await session.execute(
        select(ClubSettings).where(ClubSettings.setting_key == key)
    )
    setting = result.scalar_one_or_none()
    return setting.setting_value if setting else None


async def set_setting(session: AsyncSession, key: str, value: Optional[str]) -> ClubSettings:
    """Встановити значення налаштування (оновити якщо існує, створити якщо немає)"""
    result = await session.execute(
        select(ClubSettings).where(ClubSettings.setting_key == key)
    )
    setting = result.scalar_one_or_none()
    
    if setting:
        # Оновлюємо існуюче
        setting.setting_value = value
        setting.updated_at = datetime.utcnow()
    else:
        # Створюємо нове
        setting = ClubSettings(
            setting_key=key,
            setting_value=value
        )
        session.add(setting)
    
    await session.commit()
    await session.refresh(setting)
    return setting


async def get_all_settings(session: AsyncSession) -> dict:
    """Отримати всі налаштування як словник"""
    result = await session.execute(select(ClubSettings))
    settings = result.scalars().all()
    return {s.setting_key: s.setting_value for s in settings}
