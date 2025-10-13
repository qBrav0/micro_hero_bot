from sqlmodel import SQLModel, create_engine, Session
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/gameclub.db")

# Створюємо асинхронний движок
engine = create_async_engine(DATABASE_URL, echo=False, future=True)

# Створюємо фабрику сесій
async_session = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


async def init_db():
    """Ініціалізація бази даних"""
    # Створюємо папку data якщо її немає
    data_dir = os.path.dirname(DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """Отримати сесію бази даних"""
    async with async_session() as session:
        yield session
