"""
Автоматичні міграції бази даних
"""
import logging
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


async def run_migrations(engine: AsyncEngine):
    """
    Виконує всі необхідні міграції бази даних
    """
    logger.info("🔄 Перевірка та виконання міграцій...")
    
    async with engine.begin() as conn:
        try:
            # Міграція 1: Зміна telegram_id на BIGINT
            await migrate_telegram_id_to_bigint(conn)
            
            # Міграція 2: Додавання полів для нагадувань
            await migrate_add_reminder_fields(conn)
            
            # Міграція 3: Створення таблиці для відстеження відправлених нагадувань
            await migrate_create_reminder_sent_table(conn)
            
            logger.info("✅ Всі міграції виконано успішно")
            
        except Exception as e:
            logger.error(f"❌ Помилка під час виконання міграцій: {e}")
            raise


async def migrate_telegram_id_to_bigint(conn):
    """
    Змінює тип стовпця telegram_id з INTEGER на BIGINT
    Тільки для PostgreSQL - SQLite не потребує цієї міграції
    """
    try:
        # Визначаємо тип БД
        db_name = conn.engine.dialect.name
        
        # SQLite не потребує цієї міграції (INTEGER вже підтримує великі числа)
        if db_name == 'sqlite':
            logger.info("ℹ️ SQLite: міграція telegram_id не потрібна")
            return
        
        # Тільки для PostgreSQL
        if db_name != 'postgresql':
            logger.info(f"ℹ️ База даних {db_name}: міграція telegram_id не підтримується")
            return
        
        # Перевіряємо чи існує таблиця user
        result = await conn.execute(text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables 
                WHERE table_name = 'user'
            );
            """
        ))
        table_exists = result.scalar()
        
        if not table_exists:
            logger.info("ℹ️ Таблиця user ще не створена, міграція буде застосована при створенні")
            return
        
        # Перевіряємо поточний тип стовпця telegram_id
        result = await conn.execute(text(
            """
            SELECT data_type 
            FROM information_schema.columns 
            WHERE table_name = 'user' AND column_name = 'telegram_id';
            """
        ))
        current_type = result.scalar()
        
        if current_type == 'bigint':
            logger.info("ℹ️ Стовпець telegram_id вже має тип BIGINT")
            return
        
        logger.info(f"🔄 Міграція telegram_id: {current_type} -> BIGINT")
        
        # Виконуємо міграцію
        await conn.execute(text(
            'ALTER TABLE "user" ALTER COLUMN telegram_id TYPE BIGINT;'
        ))
        
        logger.info("✅ Міграція telegram_id успішно виконана")
        
    except Exception as e:
        logger.error(f"❌ Помилка при міграції telegram_id: {e}")
        raise


async def migrate_add_reminder_fields(conn):
    """
    Додає поля reminder_enabled та reminder_hours_before до таблиці user
    """
    try:
        # Визначаємо тип БД
        db_name = conn.engine.dialect.name
        
        # Перевіряємо чи існує таблиця user
        if db_name == 'sqlite':
            result = await conn.execute(text(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='user';
                """
            ))
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'user'
                );
                """
            ))
        
        table_exists = result.scalar()
        
        if not table_exists:
            logger.info("ℹ️ Таблиця user ще не створена, міграція буде застосована при створенні")
            return
        
        # Перевіряємо чи вже існує поле reminder_enabled
        if db_name == 'sqlite':
            result = await conn.execute(text(
                "PRAGMA table_info(user);"
            ))
            columns = [row[1] for row in result.fetchall()]
            column_exists = 'reminder_enabled' in columns
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'reminder_enabled'
                );
                """
            ))
            column_exists = result.scalar()
        
        if column_exists:
            logger.info("ℹ️ Поля для нагадувань вже існують")
            return
        
        logger.info("🔄 Додавання полів для нагадувань до таблиці user")
        
        # Додаємо поля
        if db_name == 'sqlite':
            await conn.execute(text(
                'ALTER TABLE "user" ADD COLUMN reminder_enabled BOOLEAN DEFAULT 0 NOT NULL;'
            ))
            await conn.execute(text(
                'ALTER TABLE "user" ADD COLUMN reminder_hours_before INTEGER;'
            ))
        else:  # PostgreSQL
            await conn.execute(text(
                'ALTER TABLE "user" ADD COLUMN reminder_enabled BOOLEAN DEFAULT FALSE NOT NULL;'
            ))
            await conn.execute(text(
                'ALTER TABLE "user" ADD COLUMN reminder_hours_before INTEGER;'
            ))
        
        logger.info("✅ Поля для нагадувань успішно додано")
        
    except Exception as e:
        logger.error(f"❌ Помилка при додаванні полів для нагадувань: {e}")
        raise


async def migrate_create_reminder_sent_table(conn):
    """
    Створює таблицю remindersent для відстеження відправлених нагадувань
    """
    try:
        # Визначаємо тип БД
        db_name = conn.engine.dialect.name
        
        # Перевіряємо чи існує таблиця remindersent
        if db_name == 'sqlite':
            result = await conn.execute(text(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='remindersent';
                """
            ))
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'remindersent'
                );
                """
            ))
        
        table_exists = result.scalar()
        
        if table_exists:
            logger.info("ℹ️ Таблиця remindersent вже існує")
            return
        
        logger.info("🔄 Створення таблиці remindersent")
        
        # Створюємо таблицю
        if db_name == 'sqlite':
            await conn.execute(text(
                """
                CREATE TABLE remindersent (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    session_date DATE NOT NULL,
                    sent_at DATETIME NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES user (id)
                );
                """
            ))
        else:  # PostgreSQL
            await conn.execute(text(
                """
                CREATE TABLE remindersent (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    session_date DATE NOT NULL,
                    sent_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES "user" (id)
                );
                """
            ))
        
        logger.info("✅ Таблиця remindersent успішно створена")
        
    except Exception as e:
        logger.error(f"❌ Помилка при створенні таблиці remindersent: {e}")
        raise

