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

# Копіюємо скрипт запуску
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Запускаємо через скрипт
CMD ["/app/start.sh"]

