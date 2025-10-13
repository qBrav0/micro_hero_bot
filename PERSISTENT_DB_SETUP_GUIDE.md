# 🗄️ Гайд: Налаштування Persistent БД на Railway

## 🚨 Проблема: БД втрачається при деплої

Якщо ваші дані все ще втрачаються при деплої, це означає, що Railway volume не працює правильно.

## 🔍 Діагностика проблеми

### 1. Перевірка поточного стану

Зайдіть в Railway Dashboard і перевірте:

1. **Volumes tab** - чи є там volume з назвою `bot-data`?
2. **Deployments tab** - чи показує логи створення volume?
3. **Variables tab** - чи є змінна `DATABASE_URL`?

### 2. Перевірка логів деплою

В логах Railway має бути:
```
✅ Volume mounted at /app/data
✅ Database initialized
```

Якщо немає - volume не підключився.

## 🛠️ Рішення: Покрокове налаштування

### Крок 1: Перевірка railway.json

Ваш `railway.json` має виглядати так:

```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {
    "builder": "DOCKERFILE"
  },
  "deploy": {
    "startCommand": "python main.py",
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 10
  },
  "volumes": [
    {
      "name": "bot-data",
      "mountPath": "/app/data"
    }
  ]
}
```

### Крок 2: Перевірка database.py

Переконайтеся, що в `database/database.py` є:

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./data/gameclub.db")

async def init_db():
    """Ініціалізація бази даних"""
    # Створюємо папку data якщо її немає
    data_dir = os.path.dirname(DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

### Крок 3: Альтернативне рішення через Railway Dashboard

Якщо volume через `railway.json` не працює:

#### 3.1 Створення volume вручну:

1. Зайдіть в Railway Dashboard
2. Перейдіть на вкладку **"Volumes"**
3. Натисніть **"Create volume"**
4. Вкажіть:
   - **Name**: `bot-data`
   - **Mount path**: `/app/data`
5. Натисніть **"Create"**

#### 3.2 Налаштування змінної середовища:

1. Перейдіть на вкладку **"Variables"**
2. Додайте змінну:
   - **Name**: `DATABASE_URL`
   - **Value**: `sqlite+aiosqlite:///app/data/gameclub.db`

### Крок 4: Альтернативне рішення - PostgreSQL

Якщо SQLite volume не працює, перейдіть на PostgreSQL:

#### 4.1 Додавання PostgreSQL сервісу:

1. В Railway Dashboard натисніть **"+ New"**
2. Оберіть **"Database"** → **"PostgreSQL"**
3. Додайте змінну `DATABASE_URL` з URL PostgreSQL

#### 4.2 Зміна database.py:

```python
import os
from sqlmodel import SQLModel
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from typing import AsyncGenerator

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql+asyncpg://postgres:password@localhost/gameclub")

# Для PostgreSQL використовуємо postgresql+asyncpg
engine = create_async_engine(DATABASE_URL, echo=False, future=True)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def init_db():
    """Ініціалізація бази даних"""
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

#### 4.3 Оновлення requirements.txt:

Додайте:
```
asyncpg==0.29.0
psycopg2-binary==2.9.9
```

## 🔄 Тестування рішення

### 1. Локальне тестування:

```bash
# Створіть тестові дані
python -c "
import asyncio
from database import init_db, get_session
from database.models import Game
from database.crud import create_game

async def test():
    await init_db()
    async for session in get_session():
        game = await create_game(
            session=session,
            name='Test Game',
            description='Test Description',
            min_players=2,
            max_players=4,
            avg_duration=60
        )
        print(f'Created game: {game.name}')

asyncio.run(test())
"
```

### 2. Тестування на Railway:

1. Задеплойте зміни
2. Перевірте логи - має бути:
   ```
   ✅ База даних ініціалізована
   ✅ Бот запущено
   ```
3. Створіть тестові дані через бота
4. Зробіть новий деплой
5. Перевірте, чи залишились дані

## 🚨 Якщо нічого не допомагає

### Варіант 1: Перевірка прав доступу

Додайте в `database.py`:

```python
import os
import stat

async def init_db():
    """Ініціалізація бази даних"""
    # Створюємо папку data якщо її немає
    data_dir = os.path.dirname(DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        # Встановлюємо правильні права доступу
        os.chmod(data_dir, stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
```

### Варіант 2: Використання абсолютного шляху

```python
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:////app/data/gameclub.db")
```

### Варіант 3: Додавання логування

```python
import logging
logger = logging.getLogger(__name__)

async def init_db():
    """Ініціалізація бази даних"""
    logger.info(f"Initializing DB with URL: {DATABASE_URL}")
    
    # Створюємо папку data якщо її немає
    data_dir = os.path.dirname(DATABASE_URL.replace("sqlite+aiosqlite:///", ""))
    logger.info(f"Data directory: {data_dir}")
    
    if data_dir and not os.path.exists(data_dir):
        os.makedirs(data_dir, exist_ok=True)
        logger.info(f"Created directory: {data_dir}")
    
    async with engine.begin() as conn:
        await conn.run_sync(SQLModel.metadata.create_all)
        logger.info("Database tables created")
```

## 📞 Підтримка Railway

Якщо volume все ще не працює:

1. **Railway Discord**: https://discord.gg/railway
2. **Railway Docs**: https://docs.railway.app/
3. **GitHub Issues**: Створіть issue з логами деплою

---

**💡 Рекомендація**: Почніть з PostgreSQL - він надійніший для production і автоматично persistent на Railway.
