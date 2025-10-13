from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import os
from dotenv import load_dotenv

load_dotenv()

# Отримуємо DATABASE_URL і конвертуємо для asyncpg
DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/gameclub")

# Якщо URL починається з postgresql:// (без asyncpg), додаємо asyncpg
if DATABASE_URL.startswith("postgresql://"):
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Створюємо асинхронний движок
engine = create_async_engine(
    DATABASE_URL, 
    echo=False, 
    future=True,
    pool_pre_ping=True,  # Перевірка з'єднання перед використанням
    pool_size=10,  # Розмір пулу з'єднань
    max_overflow=20  # Максимальна кількість додаткових з'єднань
)

# Створюємо фабрику сесій
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """Ініціалізація бази даних"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Отримати сесію бази даних"""
    async with async_session() as session:
        yield session
