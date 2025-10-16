# Використовуємо офіційний Python образ
FROM python:3.11-slim

# Встановлюємо робочу директорію
WORKDIR /app

# Копіюємо файл залежностей
COPY requirements.txt .

# Встановлюємо Python залежності
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копіюємо весь проект
COPY . .

# Створюємо директорію для логів та зображень
# Примітка: /app/static/images буде підключено як Railway Persistent Volume
RUN mkdir -p /app/logs /app/static/images

# Встановлюємо правильні права доступу для volume
RUN chmod 755 /app/static/images

# Встановлюємо змінну середовища для Python
ENV PYTHONUNBUFFERED=1

# Копіюємо скрипт запуску
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

# Запускаємо через скрипт
CMD ["/app/start.sh"]

