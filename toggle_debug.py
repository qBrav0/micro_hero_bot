#!/usr/bin/env python3
"""
Простий скрипт для швидкого перемикання DEBUG_MODE
"""

import os
import sys

# Налаштування кодування для Windows
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

def toggle_debug_mode():
    """Перемикає DEBUG_MODE між TRUE та FALSE"""
    env_file = ".env"
    
    if not os.path.exists(env_file):
        print("❌ Файл .env не знайдено!")
        print("💡 Скопіюйте env.example в .env і налаштуйте його")
        return False
    
    # Читаємо поточний .env файл
    with open(env_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Знаходимо та змінюємо DEBUG_MODE
    updated = False
    for i, line in enumerate(lines):
        if line.startswith('DEBUG_MODE='):
            current_value = line.strip().split('=')[1].upper()
            new_value = "FALSE" if current_value == "TRUE" else "TRUE"
            lines[i] = f'DEBUG_MODE={new_value}\n'
            updated = True
            print(f"🔄 DEBUG_MODE змінено з {current_value} на {new_value}")
            break
    
    if not updated:
        print("❌ DEBUG_MODE не знайдено в .env файлі!")
        return False
    
    # Записуємо оновлений файл
    with open(env_file, 'w', encoding='utf-8') as f:
        f.writelines(lines)
    
    # Показуємо поточний стан
    new_mode = "TRUE" if lines[lines.index(f'DEBUG_MODE=FALSE\n') if 'DEBUG_MODE=FALSE\n' in lines else lines.index(f'DEBUG_MODE=TRUE\n')].strip().split('=')[1] == "TRUE" else "FALSE"
    
    if new_mode == "TRUE":
        print("🔧 Тепер використовується локальна SQLite база даних")
        print("💡 Для ініціалізації локальної БД запустіть: python init_local_db.py")
    else:
        print("🚀 Тепер використовується продакшн PostgreSQL база даних")
        print("⚠️  УВАГА: Будьте обережні з даними на сервері!")
    
    return True

if __name__ == "__main__":
    toggle_debug_mode()
