# 🔄 Міграція з SQLite на PostgreSQL

## 📋 Зміни, які було зроблено

Проєкт було успішно мігровано з SQLite на PostgreSQL з підтримкою asyncpg.

### 1. Оновлено залежності

**Файл: `pyproject.toml`**
- ❌ Видалено: `aiosqlite>=0.19.0`
- ✅ Додано: `asyncpg>=0.29.0`
- ✅ Додано: `psycopg2-binary>=2.9.9`

**Новий файл: `requirements.txt`**
- Створено для зручності встановлення залежностей

### 2. Оновлено підключення до бази даних

**Файл: `database/database.py`**
- Змінено DATABASE_URL з SQLite на PostgreSQL
- Додано параметри пулу з'єднань для PostgreSQL:
  - `pool_pre_ping=True` - перевірка з'єднання перед використанням
  - `pool_size=10` - розмір пулу з'єднань
  - `max_overflow=20` - максимальна кількість додаткових з'єднань
- Видалено SQLite-специфічний код створення директорії `data/`

### 3. Оновлено конфігурацію

**Файл: `config.py`**
- Змінено стандартний DATABASE_URL на PostgreSQL формат
- Формат: `postgresql+asyncpg://user:password@host:port/database`

**Файл: `env.example`**
- Оновлено з вашим PostgreSQL URL:
  ```
  DATABASE_URL=postgresql+asyncpg://postgres:emftGPpePuzZXnccZWrecXhhrOCTphZm@nozomi.proxy.rlwy.net:59885/railway
  ```

### 4. Оновлено скрипт міграції

**Файл: `migrate_db.py`**
- Повністю переписано для PostgreSQL
- Використовує `asyncpg` замість `aiosqlite`
- Оновлено SQL запити для PostgreSQL:
  - `SERIAL` замість `AUTOINCREMENT`
  - `information_schema` замість `sqlite_master` і `PRAGMA`
  - `VARCHAR` замість `TEXT`

### 5. Оновлено Docker

**Файл: `Dockerfile`**
- Замінено `sqlite3` на `libpq-dev` та `gcc`
- Оновлено Python залежності
- Видалено створення директорії `/app/data` (база в PostgreSQL)

**Файл: `docker-compose.yml`**
- Видалено volume для `./data` (більше не потрібен)
- Видалено змінну середовища `DATABASE_URL` (буде з .env)

### 6. Оновлено документацію

**Файл: `README.md`**
- Оновлено розділ "Технології" - PostgreSQL замість SQLite
- Оновлено приклад DATABASE_URL в конфігурації

**Файли: `RAILWAY_DEPLOY.md` і `RENDER_DEPLOY.md`**
- Додано інструкції по створенню PostgreSQL бази в Railway
- Видалено інструкції про Volume (більше не потрібен)
- Оновлено troubleshooting для PostgreSQL

## 🚀 Як запустити проєкт

### 1. Встановіть залежності

**Через uv (рекомендовано):**
```bash
uv pip install -e .
```

**Або через pip:**
```bash
pip install -r requirements.txt
```

### 2. Створіть .env файл

```env
BOT_TOKEN=ваш_токен_від_@BotFather
ADMIN_IDS=ваш_telegram_id
DATABASE_URL=postgresql+asyncpg://postgres:emftGPpePuzZXnccZWrecXhhrOCTphZm@nozomi.proxy.rlwy.net:59885/railway
CLUB_NAME=Герої на полицях
CLUB_DESCRIPTION=Ігротека настільних ігор
```

### 3. Запустіть бота

```bash
python main.py
```

При першому запуску бот автоматично створить всі таблиці в PostgreSQL базі даних.

## 📊 Переваги PostgreSQL над SQLite

✅ **Надійність** - професійна СУБД для продакшн
✅ **Масштабованість** - підтримка великої кількості користувачів
✅ **Concurrent доступ** - краще підтримує одночасні з'єднання
✅ **Хмарна інтеграція** - легко підключити до Railway/Render
✅ **Резервне копіювання** - автоматичні бекапи на Railway
✅ **Розширений функціонал** - більше можливостей для складних запитів

## 🔧 Міграція даних зі старої SQLite бази (опціонально)

Якщо у вас вже є дані в SQLite і ви хочете їх перенести:

### Варіант 1: Ручне перенесення через адмін-панель
1. Запустіть бота з новою PostgreSQL базою
2. Додайте ігри через адмін-панель
3. Створіть розклад заново

### Варіант 2: Скрипт міграції (складніше)
Можна написати скрипт, який:
1. Читає дані зі SQLite (`gameclub.db`)
2. Записує їх в PostgreSQL

Приклад структури скрипту:
```python
import asyncio
from sqlmodel import select
from database import get_session
from database.models import Game, User, GameSession, Registration

# Читати зі SQLite та записати в PostgreSQL
```

## ✅ Перевірка роботи

Після запуску бота перевірте логи:

```
✅ Конфігурація валідна
✅ База даних ініціалізована
🤖 Бот запущено
```

Якщо все добре - бот працює з PostgreSQL! 🎉

## 🐛 Troubleshooting

### Помилка: "Could not connect to database"
- Перевірте що DATABASE_URL правильний
- Перевірте що PostgreSQL сервер доступний
- Переконайтесь що URL починається з `postgresql+asyncpg://`

### Помилка: "asyncpg not installed"
```bash
pip install asyncpg>=0.29.0
```

### Помилка: "psycopg2 not installed"
```bash
pip install psycopg2-binary>=2.9.9
```

### Помилка: "relation does not exist"
- Таблиці ще не створені
- Запустіть `python main.py` - таблиці створяться автоматично
- Або запустіть `python migrate_db.py`

## 📝 Додаткова інформація

**Ваша PostgreSQL база:**
- Host: `nozomi.proxy.rlwy.net:59885`
- Database: `railway`
- User: `postgres`

**Важливо:** Не діліться цим URL публічно! Він містить пароль доступу до бази даних.

**Резервні копії:**
Railway автоматично робить бекапи вашої бази. Ви можете відновити дані через Railway Dashboard.

**Моніторинг:**
В Railway Dashboard ви можете:
- Переглядати метрики бази даних
- Моніторити використання ресурсів
- Переглядати логи підключень

## 🎉 Готово!

Проєкт успішно мігровано на PostgreSQL. Тепер ваш бот працює з професійною базою даних!

Якщо у вас виникли питання - перевірте логи або документацію Railway.

