# 🚀 Деплой на Render.com

Простий гайд для деплою Telegram бота на безкоштовний хостинг Render.com.

## 📋 Що потрібно

1. ✅ GitHub акаунт
2. ✅ Render.com акаунт (безкоштовний)
3. ✅ Токен бота від [@BotFather](https://t.me/BotFather)
4. ✅ Ваш Telegram ID від [@userinfobot](https://t.me/userinfobot)

## 🎯 Крок 1: Підготовка GitHub репозиторію

### Створіть репозиторій на GitHub

```bash
# Ініціалізуйте git (якщо ще не зробили)
git init

# Додайте файли
git add .
git commit -m "Initial commit"

# Додайте remote репозиторій
git remote add origin https://github.com/ВАШ_USERNAME/micro_hero_bot.git

# Відправте код
git push -u origin main
```

### Важливо: Перевірте .gitignore

Переконайтесь що `.gitignore` містить:
```
.env
*.db
__pycache__/
*.log
data/
logs/
```

## 🚀 Крок 2: Деплой на Render

### 1. Зареєструйтесь на Render.com

- Перейдіть на [render.com](https://render.com)
- Натисніть "Get Started"
- Увійдіть через GitHub

### 2. Створіть новий сервіс

- Натисніть "New +" → "Background Worker"
- Оберіть "Build and deploy from a Git repository"
- Підключіть ваш GitHub репозиторій `micro_hero_bot`

### 3. Налаштуйте сервіс

**Основні налаштування:**
- **Name**: `micro-hero-bot`
- **Region**: `Frankfurt` (EU) - найближче до України
- **Branch**: `main`
- **Runtime**: `Docker`

**Dockerfile вже налаштований в проєкті!** ✅

### 4. Додайте змінні середовища

У розділі "Environment Variables" додайте:

| Ключ | Значення | Приклад |
|------|----------|---------|
| `BOT_TOKEN` | Ваш токен від BotFather | `1234567890:ABCdefGHIjklMNOpqrsTUVwxyz` |
| `ADMIN_IDS` | Ваші Telegram ID (через кому) | `123456789,987654321` |
| `DATABASE_URL` | `sqlite+aiosqlite:///./data/gameclub.db` | (вже встановлено) |
| `CLUB_NAME` | Назва вашого клубу | `Герої на полицях` |
| `CLUB_DESCRIPTION` | Опис клубу | `Ігротека настільних ігор` |

### 5. Додайте Persistent Disk

**Важливо для збереження бази даних!**

- Прокрутіть до розділу "Disks"
- Натисніть "Add Disk"
- **Name**: `bot-data`
- **Mount Path**: `/app/data`
- **Size**: `1 GB` (безкоштовно)

### 6. Деплой

- Натисніть "Create Background Worker"
- Render автоматично:
  - Склонує ваш репозиторій
  - Побудує Docker образ
  - Запустить бота

## 📊 Крок 3: Перевірка роботи

### Моніторинг логів

1. Відкрийте ваш сервіс на Render
2. Перейдіть на вкладку "Logs"
3. Ви побачите:
   ```
   ✅ Конфігурацію перевірено
   ℹ️  Встановлено X адміністраторів
   🤖 Бот запущено успішно!
   ```

### Перевірте бота

1. Відкрийте Telegram
2. Знайдіть вашого бота
3. Надішліть `/start`
4. Бот має відповісти! 🎉

## 🔄 Автоматичні оновлення

Render автоматично деплоїть при кожному push в GitHub:

```bash
# Зробіть зміни в коді
git add .
git commit -m "Update bot features"
git push

# Render автоматично деплоїть нову версію!
```

## 🛠️ Корисні команди

### Перезапуск бота

В Render Dashboard:
- Manual Deploy → "Clear build cache & deploy"

### Перегляд логів

```bash
# Або встановіть Render CLI
npm install -g @render/cli
render login
render logs -s micro-hero-bot
```

## 📈 Обмеження безкоштовного плану

- ✅ **Час роботи**: необмежено
- ⚠️ **Сон**: засинає після 15 хв неактивності
- ✅ **Пам'ять**: 512 MB
- ✅ **CPU**: спільний
- ✅ **Диск**: 1 GB безкоштовно
- ⚠️ **Час збірки**: 100 годин/місяць

### Як уникнути сну

Безкоштовний план може засинати. Рішення:
1. Upgrade до платного плану ($7/міс)
2. Використайте UptimeRobot для пінгів (не працює для Background Workers)
3. Або просто прийміть, що бот може заснути 😴

## 🚨 Troubleshooting

### Бот не запускається

**Перевірте логи:**
- Render Dashboard → вкладка "Logs"

**Типові помилки:**

1. **"Invalid BOT_TOKEN"**
   - Перевірте токен в Environment Variables
   - Токен без лапок і пробілів

2. **"Database error"**
   - Перевірте що Disk підключений до `/app/data`
   - Mount Path має бути точно `/app/data`

3. **"Build failed"**
   - Перевірте що `Dockerfile` є в репозиторії
   - Очистіть build cache і спробуйте знову

### База даних втрачається

- Переконайтесь що Persistent Disk підключений
- Mount Path: `/app/data`
- Диск не видаляйте!

### Бот не відповідає

1. Перевірте логи - чи бот запущений
2. Перевірте токен бота
3. Перевірте чи не працює інша копія бота

## 📱 Альтернативи Render

Якщо Render не підходить:

### Railway.app
- Безкоштовний план: $5 кредитів/місяць
- Простіший деплой
- [railway.app](https://railway.app)

### Fly.io
- Безкоштовний план: 3 VM
- Глобальна мережа
- [fly.io](https://fly.io)

## ✅ Checklist деплою

- [ ] Код на GitHub
- [ ] `.env` в `.gitignore`
- [ ] Render акаунт створений
- [ ] Background Worker створений
- [ ] Environment Variables додані
- [ ] Persistent Disk підключений до `/app/data`
- [ ] Деплой успішний
- [ ] Логи показують "Бот запущено"
- [ ] Бот відповідає в Telegram

## 🎉 Готово!

Ваш бот працює в хмарі 24/7! 

**Наступні кроки:**
- Додайте ігри через адмін-панель
- Створіть розклад
- Запросіть користувачів

**Успіхів!** 🚀

