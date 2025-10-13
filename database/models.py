from datetime import datetime, date, time
from typing import Optional
from sqlmodel import SQLModel, Field


class User(SQLModel, table=True):
    """Модель користувача"""
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int = Field(unique=True, index=True)
    username: Optional[str] = None
    first_name: str
    last_name: Optional[str] = None
    is_admin: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Game(SQLModel, table=True):
    """Модель гри"""
    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(index=True)
    description: str
    min_players: int
    max_players: int
    avg_duration: int  # в хвилинах
    image_path: Optional[str] = None
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class GameSession(SQLModel, table=True):
    """Модель сесії гри в розкладі"""
    id: Optional[int] = Field(default=None, primary_key=True)
    game_id: int = Field(foreign_key="game.id")
    date: date
    start_time: time
    end_time: time
    created_by: int = Field(foreign_key="user.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Registration(SQLModel, table=True):
    """Модель реєстрації на гру"""
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    session_id: int = Field(foreign_key="gamesession.id")
    registered_at: datetime = Field(default_factory=datetime.utcnow)
    is_active: bool = Field(default=True)
