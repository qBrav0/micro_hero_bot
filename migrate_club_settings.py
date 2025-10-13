"""
Міграція: додавання таблиці ClubSettings для зберігання налаштувань клубу в БД

Цей скрипт:
1. Створює таблицю clubsettings якщо її ще немає
2. Мігрує початкові значення з .env (CLUB_ABOUT_TEXT, PAYMENT_INFO тощо) в БД
"""
import asyncio
import os
from dotenv import load_dotenv

from database import init_db, get_session, set_setting


async def migrate():
    """Виконати міграцію"""
    print("🔄 Початок міграції ClubSettings...")
    
    # Завантажуємо .env
    load_dotenv()
    
    # Ініціалізуємо БД (створить таблицю якщо її немає)
    print("📦 Ініціалізація бази даних...")
    await init_db()
    print("✅ База даних ініціалізована")
    
    # Отримуємо значення з .env
    club_about_text = os.getenv("CLUB_ABOUT_TEXT")
    payment_info = os.getenv("PAYMENT_INFO")
    payment_card_number = os.getenv("PAYMENT_CARD_NUMBER")
    payment_bank_link = os.getenv("PAYMENT_BANK_LINK")
    
    # Зберігаємо в БД
    print("\n💾 Міграція налаштувань з .env в базу даних...")
    
    async for session in get_session():
        if club_about_text:
            await set_setting(session, "CLUB_ABOUT_TEXT", club_about_text)
            print(f"✅ CLUB_ABOUT_TEXT: збережено")
        else:
            print(f"ℹ️  CLUB_ABOUT_TEXT: не знайдено в .env, пропущено")
        
        if payment_info:
            await set_setting(session, "PAYMENT_INFO", payment_info)
            print(f"✅ PAYMENT_INFO: збережено")
        else:
            print(f"ℹ️  PAYMENT_INFO: не знайдено в .env, пропущено")
        
        if payment_card_number:
            await set_setting(session, "PAYMENT_CARD_NUMBER", payment_card_number)
            print(f"✅ PAYMENT_CARD_NUMBER: збережено")
        else:
            print(f"ℹ️  PAYMENT_CARD_NUMBER: не знайдено в .env, пропущено")
        
        if payment_bank_link:
            await set_setting(session, "PAYMENT_BANK_LINK", payment_bank_link)
            print(f"✅ PAYMENT_BANK_LINK: збережено")
        else:
            print(f"ℹ️  PAYMENT_BANK_LINK: не знайдено в .env, пропущено")
    
    print("\n🎉 Міграція успішно завершена!")
    print("\n📝 Тепер налаштування клубу зберігаються в PostgreSQL і")
    print("   будуть оновлюватися динамічно через адмін-панель бота.")


if __name__ == "__main__":
    try:
        asyncio.run(migrate())
    except Exception as e:
        print(f"\n❌ Помилка при міграції: {e}")
        import traceback
        traceback.print_exc()

