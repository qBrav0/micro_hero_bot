#!/usr/bin/env python3
"""
Скрипт для ініціалізації локальної бази даних
Використовується для створення чи оновлення локальної SQLite бази даних
"""

import asyncio
import os
import sys
from pathlib import Path

# Додаємо поточну директорію до шляху Python
sys.path.append(str(Path(__file__).parent))

from database.database import init_db, engine
from database.models import *
from config import DEBUG_MODE, DATABASE_URL

async def main():
    """Ініціалізація локальної бази даних"""
    print(f"🔧 Ініціалізація локальної бази даних...")
    print(f"🐛 DEBUG_MODE: {DEBUG_MODE}")
    print(f"🗄️  База даних: {DATABASE_URL}")
    
    # Перевіряємо, чи це режим налагодження
    if not DEBUG_MODE:
        print("⚠️  УВАГА: Ви знаходитесь в продакшн режимі!")
        response = input("Продовжити? (y/N): ")
        if response.lower() != 'y':
            print("❌ Операція скасована")
            return
    
    try:
        # Створюємо директорію data якщо її немає
        os.makedirs("data", exist_ok=True)
        
        # Ініціалізуємо базу даних
        await init_db()
        print("✅ Локальна база даних успішно ініціалізована!")
        
        # Показуємо інформацію про файл бази даних
        if "sqlite" in DATABASE_URL:
            db_path = DATABASE_URL.split("///")[-1]
            if os.path.exists(db_path):
                size = os.path.getsize(db_path)
                print(f"📁 Файл бази даних: {db_path}")
                print(f"📊 Розмір: {size} байт")
        
    except Exception as e:
        print(f"❌ Помилка при ініціалізації бази даних: {e}")
        return
    
    finally:
        # Закриваємо з'єднання
        await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
