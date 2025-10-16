#!/usr/bin/env python3
"""
Міграція: додати поле image_file_id до таблиці Game
"""
import asyncio
from database import get_session
from sqlalchemy import text


async def add_image_file_id_column():
    """Додати колонку image_file_id до таблиці game"""
    async for session in get_session():
        try:
            # Перевіряємо, чи колонка вже існує
            check_query = text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name='game' AND column_name='image_file_id';
            """)
            result = await session.execute(check_query)
            exists = result.fetchone()
            
            if not exists:
                # Додаємо колонку
                alter_query = text("""
                    ALTER TABLE game 
                    ADD COLUMN image_file_id VARCHAR NULL;
                """)
                await session.execute(alter_query)
                await session.commit()
                print("✅ Колонку image_file_id успішно додано!")
            else:
                print("ℹ️  Колонка image_file_id вже існує")
                
        except Exception as e:
            print(f"❌ Помилка міграції: {e}")
            print("ℹ️  Можливо, ви використовуєте SQLite. Міграція буде застосована автоматично.")


if __name__ == "__main__":
    asyncio.run(add_image_file_id_column())
