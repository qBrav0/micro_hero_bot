# 🚀 Деплой на Railway.app

Простий гайд для деплою Telegram бота на безкоштовний хостинг Railway.app.

## 📋 Що потрібно

1. ✅ GitHub акаунт
2. ✅ Токен бота від [@BotFather](https://t.me/BotFather)
3. ✅ Ваш Telegram ID від [@userinfobot](https://t.me/userinfobot)

**💰 Безкоштовно:** $5 кредитів щомісяця (вистачить для бота 24/7)

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

## 🚀 Крок 2: Деплой на Railway

### 1. Зареєструйтесь на Railway.app

- Перейдіть на [railway.app](https://railway.app)
- Натисніть "Login" або "Start a New Project"
- Увійдіть через GitHub

### 2. Створіть новий проєкт

- Натисніть "New Project"
- Оберіть "Deploy from GitHub repo"
- Знайдіть і оберіть репозиторій `micro_hero_bot`
- Railway автоматично виявить Dockerfile! ✅

### 3. Додайте змінні середовища

**Важливо:** Бот не запуститься без цих змінних!

1. Відкрийте ваш деплой на Railway
2. Перейдіть на вкладку "Variables"
3. Додайте змінні (кнопка "New Variable"):

| Змінна | Значення | Де взяти |
|--------|----------|----------|
| `BOT_TOKEN` | Токен вашого бота | [@BotFather](https://t.me/BotFather) → /newbot |
| `ADMIN_IDS` | Ваш Telegram ID | [@userinfobot](https://t.me/userinfobot) |
| `DATABASE_URL` | PostgreSQL URL | Railway → New → Database → PostgreSQL → Copy URL |
| `CLUB_NAME` | `Герої на полицях` | Або ваша назва |
| `CLUB_DESCRIPTION` | `Ігротека настільних ігор` | Або ваш опис |

**Приклад ADMIN_IDS для кількох адмінів:** `123456789,987654321`

**Як отримати DATABASE_URL:**
1. В Railway Dashboard натисніть "New"
2. Оберіть "Database" → "Add PostgreSQL"
3. Після створення, відкрийте базу
4. Перейдіть на вкладку "Connect"
5. Скопіюйте "Postgres Connection URL"
6. Замініть `postgresql://` на `postgresql+asyncpg://`
7. Додайте цей URL в Variables вашого бота

### 4. Деплой

Railway автоматично:
- ✅ Виявить ваш Dockerfile
- ✅ Побудує Docker образ
- ✅ Запустить бота
- ✅ Автоматично перезапустить при push в GitHub

## 📊 Крок 3: Перевірка роботи

### Моніторинг логів

1. Відкрийте ваш проєкт на Railway
2. Перейдіть на вкладку "Deployments" → оберіть останній деплой
3. Натисніть "View Logs"
4. Ви побачите:
   ```
   ✅ Конфігурацію перевірено
   ℹ️  Встановлено X адміністраторів
   🤖 Бот запущено успішно!
   ```

### Перевірте бота в Telegram

1. Відкрийте Telegram
2. Знайдіть вашого бота
3. Надішліть `/start`
4. Бот має відповісти! 🎉

### Перевірте кредити

1. Railway Dashboard → Settings
2. Подивіться "Usage" - скільки кредитів використано
3. $5/місяць вистачить для бота 24/7

## 🔄 Автоматичні оновлення

Railway автоматично деплоїть при кожному push в GitHub:

```bash
# Зробіть зміни в коді
git add .
git commit -m "Update bot features"
git push

# Railway автоматично деплоїть нову версію!
```

**Вимкнути автодеплой:**
Settings → "Enable automatic deployments" (вимкнути)

## 🛠️ Управління ботом на Railway

### Перезапуск бота

1. Railway Dashboard → ваш проєкт
2. Settings → "Restart Deployment"

### Перегляд логів в реальному часі

1. Deployments → останній деплой
2. "View Logs"

### Railway CLI (опціонально)

```bash
# Встановити CLI
npm i -g @railway/cli

# Логін
railway login

# Переглянути логи
railway logs

# Перезапустити
railway up
```

## 📈 Безкоштовний план Railway

### Що ви отримуєте:

- ✅ **$5 кредитів щомісяця** (оновлюється 1-го числа)
- ✅ **Час роботи**: 24/7 без сну!
- ✅ **Пам'ять**: 512 MB
- ✅ **CPU**: 0.5 vCPU
- ✅ **Диск**: Volume для бази даних
- ✅ **Не потрібна картка**

### Скільки це коштує?

- Простий Telegram бот: **~$1-2/місяць**
- $5 кредитів **більш ніж достатньо!**
- Залишок кредитів **не переноситься** на наступний місяць

### Якщо кредити закінчаться

- Бот зупиниться до 1-го числа
- Railway надішле email
- Можна додати платіжну картку для auto-top-up

## 🚨 Troubleshooting

### Бот не запускається

**Перевірте логи:**
- Railway Dashboard → Deployments → View Logs

**Типові помилки:**

1. **"Invalid BOT_TOKEN"**
   - Перевірте змінні в Variables
   - Токен без лапок і пробілів
   - Перезапустіть деплой після додавання змінних

2. **"Database error"**
   - Перевірте що PostgreSQL база створена в Railway
   - Перевірте що DATABASE_URL правильний
   - URL має починатися з `postgresql+asyncpg://`

3. **"Build failed"**
   - Перевірте що `Dockerfile` є в репозиторії
   - Deployments → "Redeploy"

4. **"Out of credits"**
   - Перевірте Usage в Settings
   - Дочекайтесь 1-го числа (оновлення кредитів)
   - Або додайте картку для auto-top-up

### Бот не відповідає в Telegram

1. Перевірте логи - чи бот запущений
2. Перевірте токен бота
3. Переконайтесь що локальна копія бота **не запущена**
4. Telegram дозволяє лише один екземпляр бота

## 💡 Переваги Railway

### Чому Railway?

✅ **$5/міс безкоштовно** - без картки
✅ **24/7 робота** - бот не засинає
✅ **Автодеплой** - push в GitHub = автоматичне оновлення
✅ **Простота** - 5 хвилин налаштування
✅ **Логи в реальному часі** - легко дебажити
✅ **PostgreSQL база даних** - надійне зберігання даних

### Альтернативи

Якщо Railway не підходить:

**Fly.io**
- Безкоштовний: 3 VM
- ⚠️ Потрібна картка (але не списують)
- [fly.io](https://fly.io)

**VPS (Hetzner, DigitalOcean)**
- €3-5/міс
- Повний контроль
- Потрібні навички Linux

## ✅ Checklist деплою

- [ ] Код на GitHub
- [ ] `.env` в `.gitignore` (не комітимо секрети!)
- [ ] Railway акаунт створений (через GitHub)
- [ ] PostgreSQL база даних створена в Railway
- [ ] Проєкт створений з GitHub repo
- [ ] Variables додані (BOT_TOKEN, ADMIN_IDS, DATABASE_URL, тощо)
- [ ] Деплой успішний (зелений статус)
- [ ] Логи показують "🤖 Бот запущено успішно!"
- [ ] Бот відповідає в Telegram на `/start`
- [ ] Локальна копія бота **зупинена**

## 🎉 Готово!

Ваш бот працює в хмарі 24/7! 

**Наступні кроки:**
- Додайте ігри через адмін-панель
- Створіть розклад
- Запросіть користувачів

**Успіхів!** 🚀

