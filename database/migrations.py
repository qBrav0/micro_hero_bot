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
            
            # Міграція 4: Додавання поля для сповіщень від адміністратора
            await migrate_add_admin_notifications_field(conn)
            
            # Міграція 5: Додавання поля image_file_id для збереження Telegram file_id
            await migrate_add_image_file_id_field(conn)
            
            # Міграція 6: Створення таблиць для подій
            await migrate_create_events_tables(conn)
            
            # Міграція 7: Створення таблиці для відстеження відправлених нагадувань про події
            await migrate_create_event_reminder_sent_table(conn)
            
            # Міграція 8: Створення таблиці для Таємного Санти
            await migrate_create_secret_santa_table(conn)
            
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


async def migrate_add_admin_notifications_field(conn):
    """
    Додає поле admin_notifications_enabled до таблиці user
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
        
        # Перевіряємо чи вже існує поле admin_notifications_enabled
        if db_name == 'sqlite':
            result = await conn.execute(text(
                "PRAGMA table_info(user);"
            ))
            columns = [row[1] for row in result.fetchall()]
            column_exists = 'admin_notifications_enabled' in columns
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'admin_notifications_enabled'
                );
                """
            ))
            column_exists = result.scalar()
        
        if column_exists:
            logger.info("ℹ️ Поле admin_notifications_enabled вже існує")
            return
        
        logger.info("🔄 Додавання поля admin_notifications_enabled до таблиці user")
        
        # Додаємо поле
        if db_name == 'sqlite':
            await conn.execute(text(
                'ALTER TABLE "user" ADD COLUMN admin_notifications_enabled BOOLEAN DEFAULT 1 NOT NULL;'
            ))
        else:  # PostgreSQL
            await conn.execute(text(
                'ALTER TABLE "user" ADD COLUMN admin_notifications_enabled BOOLEAN DEFAULT TRUE NOT NULL;'
            ))
        
        logger.info("✅ Поле admin_notifications_enabled успішно додано")
        
    except Exception as e:
        logger.error(f"❌ Помилка при додаванні поля admin_notifications_enabled: {e}")
        raise


async def migrate_add_image_file_id_field(conn):
    """
    Додає поле image_file_id до таблиці game для збереження Telegram file_id
    """
    try:
        # Визначаємо тип БД
        db_name = conn.engine.dialect.name
        
        # Перевіряємо чи існує таблиця game
        if db_name == 'sqlite':
            result = await conn.execute(text(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='game';
                """
            ))
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'game'
                );
                """
            ))
        
        table_exists = result.scalar()
        
        if not table_exists:
            logger.info("ℹ️ Таблиця game ще не створена, міграція буде застосована при створенні")
            return
        
        # Перевіряємо чи вже існує поле image_file_id
        if db_name == 'sqlite':
            result = await conn.execute(text(
                "PRAGMA table_info(game);"
            ))
            columns = [row[1] for row in result.fetchall()]
            column_exists = 'image_file_id' in columns
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.columns 
                    WHERE table_name = 'game' AND column_name = 'image_file_id'
                );
                """
            ))
            column_exists = result.scalar()
        
        if column_exists:
            logger.info("ℹ️ Поле image_file_id вже існує")
            return
        
        logger.info("🔄 Додавання поля image_file_id до таблиці game")
        
        # Додаємо поле
        await conn.execute(text(
            'ALTER TABLE game ADD COLUMN image_file_id VARCHAR;'
        ))
        
        logger.info("✅ Поле image_file_id успішно додано")
        
    except Exception as e:
        logger.error(f"❌ Помилка при додаванні поля image_file_id: {e}")
        raise


async def migrate_create_events_tables(conn):
    """
    Створює таблиці event та eventregistration для системи подій
    """
    try:
        # Визначаємо тип БД
        db_name = conn.engine.dialect.name
        
        # Перевіряємо чи існує таблиця event
        if db_name == 'sqlite':
            result = await conn.execute(text(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='event';
                """
            ))
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'event'
                );
                """
            ))
        
        table_exists = result.scalar()
        
        if not table_exists:
            logger.info("🔄 Створення таблиці event")
            
            # Створюємо таблицю event
            if db_name == 'sqlite':
                await conn.execute(text(
                    """
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
                    );
                    """
                ))
                
                # Створюємо індекс для title
                await conn.execute(text(
                    "CREATE INDEX ix_event_title ON event (title);"
                ))
            else:  # PostgreSQL
                await conn.execute(text(
                    """
                    CREATE TABLE event (
                        id SERIAL PRIMARY KEY,
                        title VARCHAR NOT NULL,
                        description VARCHAR NOT NULL,
                        min_participants INTEGER NOT NULL,
                        max_participants INTEGER NOT NULL,
                        date DATE NOT NULL,
                        start_time TIME NOT NULL,
                        end_time TIME NOT NULL,
                        payment_type VARCHAR DEFAULT 'included',
                        image_file_id VARCHAR,
                        is_active BOOLEAN DEFAULT TRUE,
                        created_by INTEGER NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (created_by) REFERENCES "user" (id)
                    );
                    """
                ))
                
                # Створюємо індекс для title
                await conn.execute(text(
                    "CREATE INDEX ix_event_title ON event (title);"
                ))
            
            logger.info("✅ Таблиця event успішно створена")
        else:
            logger.info("ℹ️ Таблиця event вже існує")
        
        # Перевіряємо чи існує таблиця eventregistration
        if db_name == 'sqlite':
            result = await conn.execute(text(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='eventregistration';
                """
            ))
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'eventregistration'
                );
                """
            ))
        
        table_exists = result.scalar()
        
        if not table_exists:
            logger.info("🔄 Створення таблиці eventregistration")
            
            # Створюємо таблицю eventregistration
            if db_name == 'sqlite':
                await conn.execute(text(
                    """
                    CREATE TABLE eventregistration (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        event_id INTEGER NOT NULL,
                        registered_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT 1,
                        FOREIGN KEY (user_id) REFERENCES user (id),
                        FOREIGN KEY (event_id) REFERENCES event (id)
                    );
                    """
                ))
            else:  # PostgreSQL
                await conn.execute(text(
                    """
                    CREATE TABLE eventregistration (
                        id SERIAL PRIMARY KEY,
                        user_id INTEGER NOT NULL,
                        event_id INTEGER NOT NULL,
                        registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        is_active BOOLEAN DEFAULT TRUE,
                        FOREIGN KEY (user_id) REFERENCES "user" (id),
                        FOREIGN KEY (event_id) REFERENCES event (id)
                    );
                    """
                ))
            
            logger.info("✅ Таблиця eventregistration успішно створена")
        else:
            logger.info("ℹ️ Таблиця eventregistration вже існує")
        
    except Exception as e:
        logger.error(f"❌ Помилка при створенні таблиць подій: {e}")
        raise


async def migrate_create_event_reminder_sent_table(conn):
    """
    Створює таблицю eventremindersent для відстеження відправлених нагадувань про події
    """
    try:
        # Визначаємо тип БД
        db_name = conn.engine.dialect.name
        
        # Перевіряємо чи існує таблиця eventremindersent
        if db_name == 'sqlite':
            result = await conn.execute(text(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='eventremindersent';
                """
            ))
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'eventremindersent'
                );
                """
            ))
        
        table_exists = result.scalar()
        
        if table_exists:
            logger.info("ℹ️ Таблиця eventremindersent вже існує")
            return
        
        logger.info("🔄 Створення таблиці eventremindersent")
        
        # Створюємо таблицю
        if db_name == 'sqlite':
            await conn.execute(text(
                """
                CREATE TABLE eventremindersent (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    event_date DATE NOT NULL,
                    sent_at DATETIME NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES user (id)
                );
                """
            ))
        else:  # PostgreSQL
            await conn.execute(text(
                """
                CREATE TABLE eventremindersent (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    event_date DATE NOT NULL,
                    sent_at TIMESTAMP NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES "user" (id)
                );
                """
            ))
        
        logger.info("✅ Таблиця eventremindersent успішно створена")
        
    except Exception as e:
        logger.error(f"❌ Помилка при створенні таблиці eventremindersent: {e}")
        raise


async def migrate_create_secret_santa_table(conn):
    """
    Створює таблицю secretsanta для функціоналу Таємного Санти
    """
    try:
        # Визначаємо тип БД
        db_name = conn.engine.dialect.name
        
        # Перевіряємо чи існує таблиця secretsanta
        if db_name == 'sqlite':
            result = await conn.execute(text(
                """
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='secretsanta';
                """
            ))
        else:  # PostgreSQL
            result = await conn.execute(text(
                """
                SELECT EXISTS (
                    SELECT 1 FROM information_schema.tables 
                    WHERE table_name = 'secretsanta'
                );
                """
            ))
        
        table_exists = result.scalar()
        
        if table_exists:
            logger.info("ℹ️ Таблиця secretsanta вже існує")
            return
        
        logger.info("🔄 Створення таблиці secretsanta")
        
        # Створюємо таблицю
        if db_name == 'sqlite':
            await conn.execute(text(
                """
                CREATE TABLE secretsanta (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    wishes VARCHAR NOT NULL,
                    assigned_to INTEGER,
                    registered_at DATETIME NOT NULL,
                    draw_completed BOOLEAN DEFAULT 0 NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES user (id),
                    FOREIGN KEY (assigned_to) REFERENCES user (id)
                );
                """
            ))
        else:  # PostgreSQL
            await conn.execute(text(
                """
                CREATE TABLE secretsanta (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL UNIQUE,
                    wishes VARCHAR NOT NULL,
                    assigned_to INTEGER,
                    registered_at TIMESTAMP NOT NULL,
                    draw_completed BOOLEAN DEFAULT FALSE NOT NULL,
                    FOREIGN KEY (user_id) REFERENCES "user" (id),
                    FOREIGN KEY (assigned_to) REFERENCES "user" (id)
                );
                """
            ))
        
        logger.info("✅ Таблиця secretsanta успішно створена")
        
    except Exception as e:
        logger.error(f"❌ Помилка при створенні таблиці secretsanta: {e}")
        raise

