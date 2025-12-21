# test_speed.py
import time
import requests
from datetime import datetime

JSONBIN_API_KEY = "$2a$10$eCHhQtmSAhD8XqkrlFgE1O6N6OKwgmHrIg.G9hlrkDKIaex3GMuiW"
MASTER_BIN_ID = "69481254ae596e708fa8aa21"

HEADERS = {
    "X-Master-Key": JSONBIN_API_KEY
}


def test_jsonbin_speed():
    start = time.time()

    try:
        response = requests.get(f"https://api.jsonbin.io/v3/b/{MASTER_BIN_ID}", headers=HEADERS)
        response.raise_for_status()

        elapsed = time.time() - start
        print(f"✅ Время запроса к JSONBin: {elapsed:.2f} сек")
        print(f"📦 Размер данных: {len(response.content)} байт")

        data = response.json()
        user_count = len(data.get("users", {}))
        session_count = len(data.get("sessions", {}))
        print(f"👥 Пользователей: {user_count}")
        print(f"📊 Сессий: {session_count}")

        # Проверяем админа
        admin_id = "8382571809"
        admin_data = data.get("users", {}).get(admin_id)
        if admin_data:
            print(f"👑 Админ найден: {admin_data}")
        else:
            print(f"❌ Админ с ID {admin_id} не найден!")

    except Exception as e:
        print(f"❌ Ошибка: {e}")

test_jsonbin_speed()