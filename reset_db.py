# reset_db.py
import json

print("🔄 Принудительный сброс базы данных...")

data = {
    "users": {
        "8382571809": {
            "user_id": 8382571809,
            "role": "admin",
            "has_access": True,
            "access_until": None,
            "created_at": "2024-12-21T12:00:00"
        }
    },
    "sessions": {},
    "transactions": {},
    "debts": {},
    "counters": {
        "session_id": 0,
        "transaction_id": 0,
        "debt_id": 0
    }
}

with open("bot_data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print("✅ База данных сброшена до начального состояния")
print("📊 Структура:")
print(f"   Пользователей: {len(data['users'])}")
print(f"   Сессий: {len(data['sessions'])}")
print(f"   Счетчик session_id: {data['counters']['session_id']}")