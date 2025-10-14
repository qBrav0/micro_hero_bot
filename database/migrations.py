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

