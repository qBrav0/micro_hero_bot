"""
Скрипт міграції бази даних PostgreSQL
Додає нові колонки до існуючих таблиць
"""
import asyncio
import asyncpg
import sys
from urllib.parse import urlparse

# Налаштування кодування для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

from database.database import DATABASE_URL


async def migrate_database():
    """Додати нові колонки до існуючих таблиць"""
    # Парсимо PostgreSQL URL
    db_url = DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://")
    
    print(f"📊 Міграція бази даних PostgreSQL...")
    
    try:
        # Підключаємось до PostgreSQL
        conn = await asyncpg.connect(db_url)
        
        try:
            # Перевіряємо чи існує таблиця gamesession
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'gamesession'
                )
            """)
            
            if table_exists:
                # Перевіряємо чи існує колонка payment_type в gamesession
                column_exists = await conn.fetchval("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.columns 
                        WHERE table_name = 'gamesession' 
                        AND column_name = 'payment_type'
                    )
                """)
                
                if not column_exists:
                    print("➕ Додаємо колонку payment_type до таблиці gamesession...")
                    await conn.execute(
                        "ALTER TABLE gamesession ADD COLUMN payment_type VARCHAR DEFAULT 'included'"
                    )
                    print("✅ Колонка payment_type додана")
                else:
                    print("ℹ️  Колонка payment_type вже існує")
            else:
                print("ℹ️  Таблиця gamesession не існує. Вона буде створена при першому запуску бота.")
            
            # Перевіряємо чи існує таблиця daypricing
            table_exists = await conn.fetchval("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_name = 'daypricing'
                )
            """)
            
            if not table_exists:
                print("➕ Створюємо таблицю daypricing...")
                await conn.execute("""
                    CREATE TABLE daypricing (
                        id SERIAL PRIMARY KEY,
                        pricing_date DATE UNIQUE NOT NULL,
                        adult_price INTEGER NOT NULL,
                        child_price INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)
                await conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS ix_daypricing_pricing_date ON daypricing (pricing_date)")
                print("✅ Таблиця daypricing створена")
            else:
                print("ℹ️  Таблиця daypricing вже існує")
            
            print("✅ Міграція завершена успішно!")
            
        finally:
            await conn.close()
            
    except Exception as e:
        print(f"❌ Помилка міграції: {e}")
        print("ℹ️  Якщо база даних порожня, таблиці будуть створені при першому запуску бота.")


if __name__ == "__main__":
    asyncio.run(migrate_database())

