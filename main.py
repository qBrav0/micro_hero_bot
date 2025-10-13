"""
Головний файл запуску Telegram бота для управління ігротекою
"""
import asyncio
import logging
import sys
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

# Імпортуємо конфігурацію
from config import BOT_TOKEN, validate_config

# Імпортуємо роутери
from handlers import start_router, user_router, admin_router, common_router

# Імпортуємо базу даних
from database import init_db

# Налаштування логування
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('bot.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


async def main():
    """Головна функція запуску бота"""
    
    # Валідація конфігурації
    try:
        validate_config()
        logger.info("✅ Конфігурація валідна")
    except ValueError as e:
        logger.error(f"❌ Помилка конфігурації: {e}")
        return
    
    # Ініціалізація бази даних
    try:
        await init_db()
        logger.info("✅ База даних ініціалізована")
    except Exception as e:
        logger.error(f"❌ Помилка ініціалізації бази даних: {e}")
        return
    
    # Ініціалізація бота та диспетчера
    bot = Bot(
        token=BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    
    # Реєстрація роутерів
    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(user_router)
    dp.include_router(admin_router)
    
    logger.info("🤖 Бот запущено")
    
    try:
        # Видаляємо старі оновлення та запускаємо polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"❌ Помилка при роботі бота: {e}")
    finally:
        await bot.session.close()
        logger.info("🛑 Бот зупинено")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}")
