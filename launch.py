# launch.py
import subprocess
import os
import sys

print("🚀 ЗАПУСК ИСПРАВЛЕННОГО БОТА")

# 1. Удаляем старую базу
if os.path.exists("bot_data.json"):
    backup_name = f"bot_data_backup_{os.path.getmtime('bot_data.json')}.json"
    os.rename("bot_data.json", backup_name)
    print(f"📦 Старая база переименована в {backup_name}")

# 2. Копируем db_fixed.py как db_local.py
with open("db_fixed.py", "r", encoding="utf-8") as src:
    content = src.read()
    with open("db_local.py", "w", encoding="utf-8") as dst:
        dst.write(content)
print("✅ База данных обновлена")

# 3. Проверяем импорты в handlers.py
print("🔧 Проверяем импорты...")
with open("handlers.py", "r", encoding="utf-8") as f:
    handlers_content = f.read()

if "from db import" in handlers_content:
    handlers_content = handlers_content.replace("from db import", "from db_local import")
    with open("handlers.py", "w", encoding="utf-8") as f:
        f.write(handlers_content)
    print("✅ Импорты исправлены")

# 4. Запускаем бота
print("\n🎮 ЗАПУСКАЕМ БОТА...")
print("   После запуска:")
print("   1. Откройте Telegram")
print("   2. Напишите /start боту")
print("   3. Создайте несколько сессий")
print("   4. Проверьте что они не смешиваются")
print("\n" + "=" * 60)

try:
    subprocess.run([sys.executable, "main.py"])
except KeyboardInterrupt:
    print("\n⏹️ Бот остановлен")