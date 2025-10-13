"""
Скрипт міграції бази даних
Додає нові колонки до існуючих таблиць
"""
import asyncio
import aiosqlite
import os
import sys

# Налаштування кодування для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from database.database import DATABASE_URL


async def migrate_database():
    """Додати нові колонки до існуючих таблиць"""
    # Отримуємо шлях до БД
    db_path = DATABASE_URL.replace("sqlite+aiosqlite:///", "")
    db_path = db_path.replace("./", "")
    
    if not os.path.exists(db_path):
        print(f"❌ База даних не знайдена: {db_path}")
        print("ℹ️  База даних буде створена при першому запуску бота.")
        return
    
    print(f"📊 Міграція бази даних: {db_path}")
    
    async with aiosqlite.connect(db_path) as db:
        # Перевіряємо чи існує колонка payment_type в gamesession
        cursor = await db.execute("PRAGMA table_info(gamesession)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]
        
        if "payment_type" not in column_names:
            print("➕ Додаємо колонку payment_type до таблиці gamesession...")
            await db.execute(
                "ALTER TABLE gamesession ADD COLUMN payment_type TEXT DEFAULT 'included'"
            )
            print("✅ Колонка payment_type додана")
        else:
            print("ℹ️  Колонка payment_type вже існує")
        
        # Перевіряємо чи існує таблиця daypricing
        cursor = await db.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='daypricing'"
        )
        table_exists = await cursor.fetchone()
        
        if not table_exists:
            print("➕ Створюємо таблицю daypricing...")
            await db.execute("""
                CREATE TABLE daypricing (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    pricing_date DATE UNIQUE NOT NULL,
                    adult_price INTEGER NOT NULL,
                    child_price INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.execute("CREATE UNIQUE INDEX ix_daypricing_pricing_date ON daypricing (pricing_date)")
            print("✅ Таблиця daypricing створена")
        else:
            print("ℹ️  Таблиця daypricing вже існує")
        
        await db.commit()
        print("✅ Міграція завершена успішно!")


if __name__ == "__main__":
    asyncio.run(migrate_database())

