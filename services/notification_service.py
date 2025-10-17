from typing import List
from aiogram import Bot
from sqlalchemy.ext.asyncio import AsyncSession
from database.models import GameSession, Game, User, Event
from database.crud import get_game, get_registrations, get_event, get_event_registrations
from utils.helpers import format_date, format_time, get_user_display_name
from config import ADMIN_IDS


class NotificationService:
    """Сервіс для сповіщень"""
    
    @staticmethod
    async def notify_admins_new_registration(
        bot: Bot,
        db_session: AsyncSession,
        game_session: GameSession,
        user: User
    ):
        """Сповістити адміністраторів про нову реєстрацію"""
        # Отримуємо гру
        game = await get_game(db_session, game_session.game_id)
        if not game:
            return
        
        # Отримуємо всіх зареєстрованих гравців
        registrations = await get_registrations(db_session, game_session.id, active_only=True)
        
        # Формуємо повідомлення
        message = "🎮 <b>Нова реєстрація!</b>\n\n"
        message += f"👤 <b>Гравець:</b> {user.first_name}"
        if user.username:
            message += f" (@{user.username})"
        message += f"\n"
        message += f"🎯 <b>Гра:</b> {game.name}\n"
        message += f"📅 <b>Дата:</b> {format_date(game_session.date)}\n"
        message += f"⏰ <b>Час:</b> {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n"
        message += f"👥 <b>Місця:</b> {len(registrations)}/{game.max_players}\n"
        
        if registrations:
            message += f"\n<b>Список гравців:</b>\n"
            
            # Отримуємо інформацію про кожного гравця
            from sqlmodel import select
            for i, reg in enumerate(registrations, 1):
                result = await db_session.execute(
                    select(User).where(User.id == reg.user_id)
                )
                player = result.scalar_one_or_none()
                
                if player:
                    player_name = player.first_name
                    if player.last_name:
                        player_name += f" {player.last_name}"
                    
                    if player.username:
                        message += f"{i}. @{player.username} ({player_name})\n"
                else:
                    message += f"{i}. {player_name}\n"
        
        # Відправляємо повідомлення всім адміністраторам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, message, parse_mode="HTML")
            except Exception as e:
                print(f"Не вдалося відправити повідомлення адміністратору {admin_id}: {e}")
    
    @staticmethod
    async def notify_admins_new_event_registration(
        bot: Bot,
        db_session: AsyncSession,
        event: Event,
        user: User
    ):
        """Сповістити адміністраторів про нову реєстрацію на подію"""
        # Отримуємо всіх зареєстрованих учасників
        registrations = await get_event_registrations(db_session, event.id, active_only=True)
        
        # Формуємо повідомлення
        message = "🎪 <b>Нова реєстрація на подію!</b>\n\n"
        message += f"👤 <b>Учасник:</b> {user.first_name}"
        if user.username:
            message += f" (@{user.username})"
        message += f"\n"
        message += f"🎯 <b>Подія:</b> {event.title}\n"
        message += f"📅 <b>Дата:</b> {format_date(event.date)}\n"
        message += f"⏰ <b>Час:</b> {format_time(event.start_time)} - {format_time(event.end_time)}\n"
        message += f"👥 <b>Місця:</b> {len(registrations)}/{event.max_participants}\n"
        
        if registrations:
            message += f"\n<b>Список учасників:</b>\n"
            
            # Отримуємо інформацію про кожного учасника
            from sqlmodel import select
            for i, reg in enumerate(registrations, 1):
                result = await db_session.execute(
                    select(User).where(User.id == reg.user_id)
                )
                participant = result.scalar_one_or_none()
                
                if participant:
                    participant_name = participant.first_name
                    if participant.last_name:
                        participant_name += f" {participant.last_name}"
                    
                    if participant.username:
                        message += f"{i}. @{participant.username} ({participant_name})\n"
                    else:
                        message += f"{i}. {participant_name}\n"
        
        # Відправляємо повідомлення всім адміністраторам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, message, parse_mode="HTML")
            except Exception as e:
                print(f"Не вдалося відправити повідомлення адміністратору {admin_id}: {e}")
    
    @staticmethod
    async def notify_admins_event_cancellation(
        bot: Bot,
        db_session: AsyncSession,
        event: Event,
        user: User
    ):
        """Сповістити адміністраторів про скасування реєстрації на подію"""
        # Отримуємо всіх зареєстрованих учасників
        registrations = await get_event_registrations(db_session, event.id, active_only=True)
        
        # Формуємо повідомлення
        message = "❌ <b>Скасування реєстрації на подію</b>\n\n"
        message += f"👤 <b>Учасник:</b> {user.first_name}"
        if user.username:
            message += f" (@{user.username})"
        message += f"\n"
        message += f"🎯 <b>Подія:</b> {event.title}\n"
        message += f"📅 <b>Дата:</b> {format_date(event.date)}\n"
        message += f"⏰ <b>Час:</b> {format_time(event.start_time)} - {format_time(event.end_time)}\n"
        message += f"👥 <b>Місця:</b> {len(registrations)}/{event.max_participants}\n"
        
        # Відправляємо повідомлення всім адміністраторам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, message, parse_mode="HTML")
            except Exception as e:
                print(f"Не вдалося відправити повідомлення адміністратору {admin_id}: {e}")
    
    @staticmethod
    async def notify_admins_cancellation(
        bot: Bot,
        db_session: AsyncSession,
        game_session: GameSession,
        user: User
    ):
        """Сповістити адміністраторів про скасування реєстрації"""
        # Отримуємо гру
        game = await get_game(db_session, game_session.game_id)
        if not game:
            return
        
        # Отримуємо всіх зареєстрованих гравців
        registrations = await get_registrations(db_session, game_session.id, active_only=True)
        
        # Формуємо повідомлення
        message = "❌ <b>Скасування реєстрації</b>\n\n"
        message += f"👤 <b>Гравець:</b> {user.first_name}"
        if user.username:
            message += f" (@{user.username})"
        message += f"\n"
        message += f"🎯 <b>Гра:</b> {game.name}\n"
        message += f"📅 <b>Дата:</b> {format_date(game_session.date)}\n"
        message += f"⏰ <b>Час:</b> {format_time(game_session.start_time)} - {format_time(game_session.end_time)}\n"
        message += f"👥 <b>Місця:</b> {len(registrations)}/{game.max_players}\n"
        
        # Відправляємо повідомлення всім адміністраторам
        for admin_id in ADMIN_IDS:
            try:
                await bot.send_message(admin_id, message, parse_mode="HTML")
            except Exception as e:
                print(f"Не вдалося відправити повідомлення адміністратору {admin_id}: {e}")
