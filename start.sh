#!/bin/bash
set -e

echo "🚀 Запуск бота..."
echo "📊 Ініціалізація бази даних..."
python -c "from database.database import init_db; import asyncio; asyncio.run(init_db())" || echo "❌ Помилка ініціалізації БД"

echo "🎮 Заповнення тестовими іграми..."
python populate_test_games.py || echo "❌ Помилка заповнення ігор"

echo "🤖 Запуск бота..."
python main.py
