"""
Конфігураційний файл для Telegram бота
"""
import os
import sys
from dotenv import load_dotenv

# Налаштування кодування для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# Завантажуємо змінні середовища з .env файлу
load_dotenv()

# Telegram Bot Token
BOT_TOKEN = os.getenv("BOT_TOKEN")

# ID адміністраторів
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "")
ADMIN_IDS = [int(id.strip()) for id in ADMIN_IDS_STR.split(",") if id.strip()]

# Режим налагодження (True = локальна БД, False = серверна БД)
DEBUG_MODE = os.getenv("DEBUG_MODE", "TRUE").upper() == "TRUE"

# База даних - залежить від режиму налагодження
if DEBUG_MODE:
    # Режим налагодження - локальна SQLite база
    DATABASE_URL = os.getenv("LOCAL_DATABASE_URL", "sqlite+aiosqlite:///./data/gameclub_local.db")
else:
    # Продакшн - PostgreSQL
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/gameclub")
    
    # Якщо URL починається з postgresql:// (без asyncpg), додаємо asyncpg
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Інформація про клуб
CLUB_NAME = os.getenv("CLUB_NAME", "Герої на полицях")
CLUB_DESCRIPTION = os.getenv("CLUB_DESCRIPTION", "Ігротека настільних ігор")
CLUB_ABOUT_TEXT = os.getenv("CLUB_ABOUT_TEXT", None)

# Інформація про оплату
PAYMENT_INFO = os.getenv("PAYMENT_INFO", None)
PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "")
PAYMENT_BANK_LINK = os.getenv("PAYMENT_BANK_LINK", "")

# Функція для динамічного оновлення конфігурації
def reload_config():
    """Перезавантажити конфігурацію з .env файлу"""
    global CLUB_NAME, CLUB_DESCRIPTION, CLUB_ABOUT_TEXT, PAYMENT_INFO, PAYMENT_CARD_NUMBER, PAYMENT_BANK_LINK, DEBUG_MODE, DATABASE_URL
    load_dotenv(override=True)
    CLUB_NAME = os.getenv("CLUB_NAME", "Герої на полицях")
    CLUB_DESCRIPTION = os.getenv("CLUB_DESCRIPTION", "Ігротека настільних ігор")
    CLUB_ABOUT_TEXT = os.getenv("CLUB_ABOUT_TEXT", None)
    PAYMENT_INFO = os.getenv("PAYMENT_INFO", None)
    PAYMENT_CARD_NUMBER = os.getenv("PAYMENT_CARD_NUMBER", "")
    PAYMENT_BANK_LINK = os.getenv("PAYMENT_BANK_LINK", "")
    
    # Оновлюємо режим налагодження та базу даних
    DEBUG_MODE = os.getenv("DEBUG_MODE", "TRUE").upper() == "TRUE"
    if DEBUG_MODE:
        DATABASE_URL = os.getenv("LOCAL_DATABASE_URL", "sqlite+aiosqlite:///./data/gameclub_local.db")
    else:
        DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost:5432/gameclub")
        if DATABASE_URL.startswith("postgresql://"):
            DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

# Валідація конфігурації
def validate_config():
    """Перевірити, що всі необхідні змінні середовища встановлені"""
    errors = []
    warnings = []
    
    if not BOT_TOKEN:
        errors.append("❌ BOT_TOKEN не встановлено в .env файлі")
    
    if not ADMIN_IDS:
        warnings.append("⚠️  ADMIN_IDS не встановлено або порожній. Ніхто не матиме доступу до адмін-панелі")
    elif len(ADMIN_IDS) == 1:
        print(f"ℹ️  Встановлено 1 адміністратора (ID: {ADMIN_IDS[0]})")
    else:
        print(f"ℹ️  Встановлено {len(ADMIN_IDS)} адміністраторів (IDs: {', '.join(map(str, ADMIN_IDS))})")
    
    if warnings:
        for warning in warnings:
            print(warning)
    
    if errors:
        for error in errors:
            print(error)
        if not BOT_TOKEN:
            raise ValueError("BOT_TOKEN є обов'язковим параметром")
    
    return True


if __name__ == "__main__":
    # Для тестування конфігурації
    validate_config()
    print("✅ Конфігурація валідна")
    print(f"🐛 DEBUG_MODE: {DEBUG_MODE}")
    print(f"📝 BOT_TOKEN: {'*' * 10}{BOT_TOKEN[-5:] if BOT_TOKEN else 'NOT SET'}")
    print(f"👥 ADMIN_IDS: {ADMIN_IDS}")
    print(f"🗄️  DATABASE_URL: {DATABASE_URL}")
    print(f"🏢 CLUB_NAME: {CLUB_NAME}")
    
    # Додаткова інформація про базу даних
    if DEBUG_MODE:
        print("🔧 Режим налагодження - використовується локальна SQLite")
    else:
        print("🚀 Продакшн режим - використовується PostgreSQL")
