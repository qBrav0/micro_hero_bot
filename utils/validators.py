from datetime import datetime, date, time
from typing import Optional, Tuple


def validate_time(time_str: str) -> Tuple[bool, Optional[time], str]:
    """
    Валідація часу у форматі HH:MM
    Повертає: (успішно, time об'єкт, повідомлення про помилку)
    """
    try:
        hours, minutes = map(int, time_str.split(':'))
        if not (0 <= hours <= 23 and 0 <= minutes <= 59):
            return False, None, "⚠️ Час повинен бути в діапазоні 00:00 - 23:59"
        return True, time(hours, minutes), ""
    except (ValueError, AttributeError):
        return False, None, "⚠️ Невірний формат часу. Використовуйте формат ЧЧ:ХХ (наприклад, 14:30)"


def validate_date(date_str: str) -> Tuple[bool, Optional[date], str]:
    """
    Валідація дати у форматі DD.MM.YYYY
    Повертає: (успішно, date об'єкт, повідомлення про помилку)
    """
    try:
        day, month, year = map(int, date_str.split('.'))
        parsed_date = date(year, month, day)
        
        if parsed_date < date.today():
            return False, None, "⚠️ Дата не може бути в минулому"
        
        return True, parsed_date, ""
    except (ValueError, AttributeError):
        return False, None, "⚠️ Невірний формат дати. Використовуйте формат ДД.ММ.РРРР (наприклад, 25.12.2024)"


def validate_players_count(min_players: int, max_players: int) -> Tuple[bool, str]:
    """
    Валідація кількості гравців
    Повертає: (успішно, повідомлення про помилку)
    """
    if min_players < 1:
        return False, "⚠️ Мінімальна кількість гравців повинна бути більше 0"
    
    if max_players < min_players:
        return False, "⚠️ Максимальна кількість гравців не може бути менше мінімальної"
    
    if max_players > 100:
        return False, "⚠️ Максимальна кількість гравців не може перевищувати 100"
    
    return True, ""


def validate_duration(duration: int) -> Tuple[bool, str]:
    """
    Валідація тривалості гри
    Повертає: (успішно, повідомлення про помилку)
    """
    if duration < 1:
        return False, "⚠️ Тривалість гри повинна бути більше 0 хвилин"
    
    if duration > 1440:  # 24 години
        return False, "⚠️ Тривалість гри не може перевищувати 1440 хвилин (24 години)"
    
    return True, ""
