#!/bin/bash
set -e

echo "=========================================="
echo "🚀 Запуск бота..."
echo "📁 Поточна директорія: $(pwd)"
echo "📋 Вміст директорії:"
ls -la
echo "=========================================="

echo "📊 Ініціалізація бази даних..."
python -c "
try:
    from database.database import init_db
    import asyncio
    asyncio.run(init_db())
    print('✅ База даних ініціалізована успішно')
except Exception as e:
    print(f'❌ Помилка ініціалізації БД: {e}')
    import traceback
    traceback.print_exc()
"

echo "🎮 Заповнення тестовими іграми..."
python populate_test_games.py || echo "❌ Помилка заповнення ігор"

echo "🤖 Запуск бота..."
python main.py
