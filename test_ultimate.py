# test_ultimate.py
import os
import json
import time

print("🧪 УЛЬТИМАТИВНЫЙ ТЕСТ СЕССИЙ")
print("=" * 60)

# Удаляем старый файл
if os.path.exists("bot_data.json"):
    os.remove("bot_data.json")
    print("🗑️ Старый файл удален")

# Импортируем после удаления файла
from db_fixed import add_session, get_user_sessions, close_session, _load_data_force

user_id = 8382571809

def print_file_content():
    """Печатает содержимое файла"""
    if os.path.exists("bot_data.json"):
        with open("bot_data.json", "r") as f:
            data = json.load(f)
            print(f"\n📁 СОДЕРЖИМОЕ ФАЙЛА:")
            print(f"   Счетчик session_id: {data['counters']['session_id']}")
            print(f"   Сессий в файле: {len(data['sessions'])}")
            for sid, sess in data['sessions'].items():
                print(f"   - Сессия {sid}: ID={sess['id']}, Имя='{sess['name']}', Пользователь={sess['user_id']}")

# 1. Создаем первую сессию
print("\n1. Создаем первую сессию...")
session1_id = add_session(user_id, "Сессия 1", 1000, "USD")
print(f"   ✅ ID: {session1_id}")
print_file_content()

# 2. Проверяем
print("\n2. Проверяем сессии...")
sessions = get_user_sessions(user_id)
print(f"   Найдено сессий: {len(sessions)}")
for s in sessions:
    print(f"   - ID: {s[0]}, Имя: '{s[1]}'")

# 3. Закрываем первую сессию
print("\n3. Закрываем первую сессию...")
close_session(session1_id)
print_file_content()

# 4. Создаем вторую сессию
print("\n4. Создаем вторую сессию...")
session2_id = add_session(user_id, "Сессия 2", 2000, "EUR")
print(f"   ✅ ID: {session2_id}")
print_file_content()

# 5. Проверяем
print("\n5. Проверяем сессии...")
sessions = get_user_sessions(user_id)
print(f"   Найдено сессий: {len(sessions)}")
for s in sessions:
    print(f"   - ID: {s[0]}, Имя: '{s[1]}', Активна: {s[4]}")

# 6. Создаем третью сессию
print("\n6. Создаем третью сессию...")
session3_id = add_session(user_id, "Сессия 3", 3000, "RUB")
print(f"   ✅ ID: {session3_id}")
print_file_content()

print("\n" + "=" * 60)
print("🎯 ОЖИДАЕМЫЙ РЕЗУЛЬТАТ:")
print("✅ Должно быть 3 разные сессии")
print("✅ ID: 1, 2, 3")
print("✅ Имена: 'Сессия 1', 'Сессия 2', 'Сессия 3'")
print("✅ В файле должны быть все 3 сессии")