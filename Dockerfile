# Використовуємо офіційний Python образ
FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Встановлюємо системні залежності
RUN apt-get update && apt-get install -y \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Копіюємо файл залежностей
COPY pyproject.toml .

# Встановлюємо Python залежності
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir aiogram>=3.0.0 sqlmodel>=0.0.14 python-dotenv>=1.0.0 aiosqlite>=0.19.0

# Копіюємо весь проект
COPY . .

# Створюємо директорію для бази даних та логів
RUN mkdir -p /app/data /app/logs /app/static/images

# Встановлюємо змінну середовища для Python
ENV PYTHONUNBUFFERED=1

# Створюємо скрипт запуску
RUN echo '#!/bin/bash\n\
set -e\n\
echo "🚀 Запуск бота..."\n\
echo "📊 Ініціалізація бази даних..."\n\
python -c "from database.database import init_db; import asyncio; asyncio.run(init_db())" || echo "❌ Помилка ініціалізації БД"\n\
echo "🎮 Заповнення тестовими іграми..."\n\
python populate_test_games.py || echo "❌ Помилка заповнення ігор"\n\
echo "🤖 Запуск бота..."\n\
python main.py' > /app/start.sh && chmod +x /app/start.sh

# Запускаємо через скрипт
CMD ["/app/start.sh"]

