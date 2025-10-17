#!/usr/bin/env python3
"""
Міграція для додавання таблиць подій
"""
import asyncio
from sqlalchemy import text
from database.database import engine


async def run_migration():
    """Виконати міграцію"""
    async with engine.begin() as conn:
        # Перевіряємо чи існує таблиця event
        result = await conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='event'
        """))
        
        if not result.fetchone():
            # Створюємо таблицю Event
            await conn.execute(text("""
                CREATE TABLE event (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title VARCHAR NOT NULL,
                    description VARCHAR NOT NULL,
                    min_participants INTEGER NOT NULL,
                    max_participants INTEGER NOT NULL,
                    date DATE NOT NULL,
                    start_time TIME NOT NULL,
                    end_time TIME NOT NULL,
                    payment_type VARCHAR DEFAULT 'included',
                    image_file_id VARCHAR,
                    is_active BOOLEAN DEFAULT 1,
                    created_by INTEGER NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (created_by) REFERENCES user (id)
                )
            """))
            
            # Створюємо індекс для title
            await conn.execute(text("""
                CREATE INDEX ix_event_title ON event (title)
            """))
            
            print("✅ Таблиця event створена")
        else:
            print("ℹ️ Таблиця event вже існує")
        
        # Перевіряємо чи існує таблиця eventregistration
        result = await conn.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='eventregistration'
        """))
        
        if not result.fetchone():
            # Створюємо таблицю EventRegistration
            await conn.execute(text("""
                CREATE TABLE eventregistration (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_id INTEGER NOT NULL,
                    registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    is_active BOOLEAN DEFAULT 1,
                    FOREIGN KEY (user_id) REFERENCES user (id),
                    FOREIGN KEY (event_id) REFERENCES event (id)
                )
            """))
            
            print("✅ Таблиця eventregistration створена")
        else:
            print("ℹ️ Таблиця eventregistration вже існує")
        
        print("✅ Міграція подій виконана успішно!")


if __name__ == "__main__":
    asyncio.run(run_migration())
