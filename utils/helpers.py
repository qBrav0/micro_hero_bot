from datetime import datetime, date, time
from typing import Optional
from aiogram import types


def format_datetime(dt: datetime) -> str:
    """Форматувати datetime для відображення"""
    return dt.strftime("%d.%m.%Y %H:%M")


def format_time(t: time) -> str:
    """Форматувати time для відображення"""
    return t.strftime("%H:%M")


def format_date(d: date) -> str:
    """Форматувати date для відображення"""
    # Словник назв днів тижня українською
    weekdays = {
        0: "Понеділок",
        1: "Вівторок",
        2: "Середа",
        3: "Четвер",
        4: "П'ятниця",
        5: "Субота",
        6: "Неділя"
    }
    
    weekday_name = weekdays[d.weekday()]
    return f"{weekday_name}, {d.strftime('%d.%m.%Y')}"


def get_user_display_name(user: types.User) -> str:
    """Отримати відображуване ім'я користувача"""
    if user.username:
        return f"@{user.username}"
    
    full_name = user.first_name
    if user.last_name:
        full_name += f" {user.last_name}"
    
    return full_name


def get_user_full_name(user: types.User) -> str:
    """Отримати повне ім'я користувача"""
    full_name = user.first_name
    if user.last_name:
        full_name += f" {user.last_name}"
    return full_name
