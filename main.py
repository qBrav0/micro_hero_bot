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
from handlers import start_router, user_router, admin_router, common_router, reminder_router, event_router

# Імпортуємо базу даних
from database import init_db, run_migrations, get_session
from database.database import engine

# Імпортуємо сервіси
from services import ReminderService

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


async def reminder_background_task(bot: Bot):
    """Фонова задача для періодичної перевірки та відправки нагадувань"""
    logger.info("🔔 Фонова задача нагадувань запущена")
    
    while True:
        try:
            logger.debug("Перевірка нагадувань...")
            
            # Отримуємо сесію БД і відправляємо нагадування
            async for session in get_session():
                await ReminderService.send_reminders(bot, session)
            
            # Перевіряємо кожні 5 хвилин
            await asyncio.sleep(300)  # 5 хвилин = 300 секунд
                
        except asyncio.CancelledError:
            logger.info("🔔 Фонова задача нагадувань зупинена")
            break
        except Exception as e:
            logger.error(f"Помилка в фоновій задачі нагадувань: {e}")
            # Продовжуємо роботу навіть при помилці
            await asyncio.sleep(300)  # Чекаємо 5 хвилин перед наступною спробою
            continue


async def on_callback_query(callback_query):
    """Middleware для логування всіх callback запитів"""
    logger.info(f"📞 [CALLBACK] Отримано callback: data='{callback_query.data}', user={callback_query.from_user.username} (ID: {callback_query.from_user.id})")


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
        # Спочатку виконуємо міграції
        await run_migrations(engine)
        # Потім ініціалізуємо таблиці
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
    
    # Реєструємо middleware для логування callback
    dp.callback_query.middleware(lambda handler, event, data: 
        logger.info(f"📞 [CALLBACK] data='{event.data}', user={event.from_user.username} (ID: {event.from_user.id})") or handler(event, data)
    )
    
    # Реєстрація роутерів
    dp.include_router(start_router)
    dp.include_router(common_router)
    dp.include_router(reminder_router)
    dp.include_router(user_router)
    dp.include_router(event_router)
    dp.include_router(admin_router)
    
    logger.info("🤖 Бот запущено")
    
    # Створюємо фонову задачу для нагадувань
    reminder_task = asyncio.create_task(reminder_background_task(bot))
    
    try:
        # Видаляємо старі оновлення та запускаємо polling
        await bot.delete_webhook(drop_pending_updates=True)
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except Exception as e:
        logger.error(f"❌ Помилка при роботі бота: {e}")
    finally:
        # Зупиняємо фонову задачу
        reminder_task.cancel()
        try:
            await reminder_task
        except asyncio.CancelledError:
            pass
        
        await bot.session.close()
        logger.info("🛑 Бот зупинено")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("🛑 Бот зупинено користувачем")
    except Exception as e:
        logger.error(f"❌ Критична помилка: {e}")
