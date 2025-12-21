# db.py
import json
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any

# --- НАСТРОЙКИ JSONBIN.IO ---
JSONBIN_API_KEY = "69481254ae596e708fa8aa21"  # Получите на https://jsonbin.io/
MASTER_BIN_ID = "$2a$10$eCHhQtmSAhD8XqkrlFgE1O6N6OKwgmHrIg.G9hlrkDKIaex3GMuiW"  # Создайте bin и вставьте ID

API_URL = "https://api.jsonbin.io/v3/b"
HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_API_KEY,
    "X-Bin-Meta": "false"
}


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ JSONBIN ---

def load_data() -> dict:
    """Загружает все данные из JSONBin"""
    try:
        response = requests.get(f"{API_URL}/{MASTER_BIN_ID}", headers=HEADERS)
        response.raise_for_status()
        data = response.json()

        # Инициализация структуры если пусто
        if not data:
            data = {
                "users": {},
                "sessions": {},
                "transactions": {},
                "debts": {},
                "counters": {
                    "session_id": 0,
                    "transaction_id": 0,
                    "debt_id": 0
                }
            }
            save_data(data)

        return data
    except Exception as e:
        print(f"Ошибка загрузки данных: {e}")
        return {
            "users": {},
            "sessions": {},
            "transactions": {},
            "debts": {},
            "counters": {
                "session_id": 0,
                "transaction_id": 0,
                "debt_id": 0
            }
        }


def save_data(data: dict):
    """Сохраняет данные в JSONBin"""
    try:
        response = requests.put(f"{API_URL}/{MASTER_BIN_ID}",
                                json=data,
                                headers=HEADERS)
        response.raise_for_status()
        return True
    except Exception as e:
        print(f"Ошибка сохранения данных: {e}")
        return False


def get_next_id(counter_name: str) -> int:
    """Получает следующий ID"""
    data = load_data()
    data["counters"][counter_name] += 1
    save_data(data)
    return data["counters"][counter_name]


# --- ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ---

def ensure_user_exists(user_id: int):
    """Создает пользователя если не существует"""
    data = load_data()
    user_id_str = str(user_id)

    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {
            "user_id": user_id,
            "role": "user",
            "has_access": False,
            "access_until": None,
            "created_at": datetime.now().isoformat()
        }
        save_data(data)


def get_user_role(user_id: int) -> str:
    """Получает роль пользователя"""
    data = load_data()
    user = data["users"].get(str(user_id))
    if user:
        return user.get("role", "user")
    return "user"


def check_user_access(user_id: int) -> bool:
    """Проверяет доступ пользователя"""
    data = load_data()
    user = data["users"].get(str(user_id))

    if not user:
        return False

    if user.get("role") == "admin":
        return True

    if not user.get("has_access", False):
        return False

    # Проверяем срок доступа
    access_until = user.get("access_until")
    if access_until:
        try:
            until_date = datetime.fromisoformat(access_until)
            if datetime.now() > until_date:
                # Срок истек
                user["has_access"] = False
                user["access_until"] = None
                save_data(data)
                return False
        except:
            pass

    return user.get("has_access", False)


def update_user_access(user_id: int, grant_access: bool, days: int = 0):
    """Обновляет доступ пользователя"""
    data = load_data()
    user_id_str = str(user_id)

    if user_id_str not in data["users"]:
        ensure_user_exists(user_id)

    user = data["users"][user_id_str]
    user["has_access"] = grant_access

    if grant_access and days > 0:
        until_date = datetime.now() + timedelta(days=days)
        user["access_until"] = until_date.isoformat()
    else:
        user["access_until"] = None

    save_data(data)


def get_all_users() -> List[Dict]:
    """Получает всех пользователей"""
    data = load_data()
    return list(data["users"].values())


def add_admin(user_id: int):
    """Добавляет администратора"""
    data = load_data()
    user_id_str = str(user_id)

    if user_id_str not in data["users"]:
        ensure_user_exists(user_id)

    data["users"][user_id_str]["role"] = "admin"
    data["users"][user_id_str]["has_access"] = True
    save_data(data)


def remove_admin(user_id: int):
    """Удаляет администратора"""
    data = load_data()
    user_id_str = str(user_id)

    if user_id_str in data["users"]:
        data["users"][user_id_str]["role"] = "user"
        save_data(data)


def grant_access_to_all():
    """Дает доступ всем пользователям"""
    data = load_data()
    for user_id, user_data in data["users"].items():
        user_data["has_access"] = True
    save_data(data)


def revoke_temporary_access():
    """Отзывает доступ у неоплативших пользователей"""
    data = load_data()
    for user_id, user_data in data["users"].items():
        if user_data.get("role") != "admin":
            user_data["has_access"] = False
            user_data["access_until"] = None
    save_data(data)


# --- ФУНКЦИИ ДЛЯ СЕССИЙ ---

def add_session(user_id: int, name: str, budget: float, currency: str) -> int:
    """Добавляет новую сессию"""
    data = load_data()

    session_id = get_next_id("session_id")

    data["sessions"][str(session_id)] = {
        "id": session_id,
        "user_id": user_id,
        "name": name[:50],
        "budget": budget,
        "currency": currency,
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }

    save_data(data)
    return session_id


def get_user_sessions(user_id: int) -> List[tuple]:
    """Получает сессии пользователя"""
    data = load_data()
    sessions = []

    for session in data["sessions"].values():
        if session["user_id"] == user_id:
            sessions.append((
                session["id"],
                session["name"],
                session["budget"],
                session["currency"],
                session["is_active"]
            ))

    return sessions


def get_session_details(session_id: int) -> Optional[Dict]:
    """Получает детали сессии с расчетами"""
    data = load_data()
    session = data["sessions"].get(str(session_id))

    if not session:
        return None

    # Рассчитываем статистику
    total_sales = 0
    total_expenses = 0
    sales_count = 0
    owed_to_me = 0
    i_owe = 0

    # Считаем транзакции
    for trans in data["transactions"].values():
        if trans["session_id"] == session_id:
            if trans["type"] == "sale":
                total_sales += trans["amount"]
                total_expenses += trans["expense_amount"]
                sales_count += 1
            elif trans["type"] == "expense":
                total_expenses += trans["amount"]

    # Считаем долги
    for debt in data["debts"].values():
        if debt["session_id"] == session_id and not debt.get("is_repaid", False):
            if debt["type"] == "owed_to_me":
                owed_to_me += debt["amount"]
            elif debt["type"] == "i_owe":
                i_owe += debt["amount"]

    balance = total_sales - total_expenses

    return {
        "id": session["id"],
        "name": session["name"],
        "budget": session["budget"],
        "currency": session["currency"],
        "is_active": session["is_active"],
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "sales_count": sales_count,
        "owed_to_me": owed_to_me,
        "i_owe": i_owe,
        "balance": balance
    }


def close_session(session_id: int):
    """Закрывает сессию"""
    data = load_data()
    session = data["sessions"].get(str(session_id))

    if session:
        session["is_active"] = False
        session["closed_at"] = datetime.now().isoformat()
        save_data(data)


# --- ФУНКЦИИ ДЛЯ ТРАНЗАКЦИЙ ---

def add_transaction(session_id: int, trans_type: str, amount: float,
                    expense_amount: float = 0, description: str = "") -> int:
    """Добавляет транзакцию (продажу или затрату)"""
    data = load_data()

    transaction_id = get_next_id("transaction_id")

    data["transactions"][str(transaction_id)] = {
        "id": transaction_id,
        "session_id": session_id,
        "type": trans_type,
        "amount": amount,
        "expense_amount": expense_amount if trans_type == "sale" else 0,
        "description": description[:100],
        "date": datetime.now().isoformat()
    }

    save_data(data)
    return transaction_id


def get_transactions_list(session_id: int, trans_type: str,
                          search_query: str = None) -> List[Dict]:
    """Получает список транзакций с фильтрацией"""
    data = load_data()
    transactions = []

    for trans in data["transactions"].values():
        if trans["session_id"] == session_id and trans["type"] == trans_type:
            # Фильтр по поиску
            if search_query:
                if search_query.lower() not in trans["description"].lower():
                    continue

            # Форматируем дату
            try:
                trans_date = datetime.fromisoformat(trans["date"])
                formatted_date = trans_date.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = trans["date"]

            transactions.append({
                "id": trans["id"],
                "description": trans["description"],
                "amount": trans["amount"],
                "expense_amount": trans.get("expense_amount", 0),
                "date": formatted_date
            })

    # Сортируем по дате (новые сначала)
    transactions.sort(key=lambda x: x["date"], reverse=True)
    return transactions


def update_transaction(trans_id: int, field: str, value: Any):
    """Обновляет поле транзакции"""
    data = load_data()
    trans = data["transactions"].get(str(trans_id))

    if trans:
        trans[field] = value
        trans["updated_at"] = datetime.now().isoformat()
        save_data(data)


def delete_transaction(trans_id: int):
    """Удаляет транзакцию"""
    data = load_data()
    if str(trans_id) in data["transactions"]:
        del data["transactions"][str(trans_id)]
        save_data(data)


# --- ФУНКЦИИ ДЛЯ ДОЛГОВ ---

def add_debt(session_id: int, debt_type: str, person_name: str,
             amount: float, description: str = "") -> int:
    """Добавляет долг"""
    data = load_data()

    debt_id = get_next_id("debt_id")

    data["debts"][str(debt_id)] = {
        "id": debt_id,
        "session_id": session_id,
        "type": debt_type,
        "person_name": person_name[:50],
        "amount": amount,
        "description": description[:100],
        "is_repaid": False,
        "created_at": datetime.now().isoformat()
    }

    save_data(data)
    return debt_id


def get_debts_list(session_id: int, debt_type: str,
                   search_query: str = None) -> List[Dict]:
    """Получает список долгов"""
    data = load_data()
    debts = []

    for debt in data["debts"].values():
        if debt["session_id"] == session_id and debt["type"] == debt_type:
            # Фильтр по поиску
            if search_query:
                if (search_query.lower() not in debt["person_name"].lower() and
                        search_query.lower() not in debt["description"].lower()):
                    continue

            # Форматируем дату
            try:
                debt_date = datetime.fromisoformat(debt["created_at"])
                formatted_date = debt_date.strftime("%d.%m.%Y %H:%M")
            except:
                formatted_date = debt["created_at"]

            debts.append({
                "id": debt["id"],
                "person_name": debt["person_name"],
                "description": debt["description"],
                "amount": debt["amount"],
                "date": formatted_date,
                "is_repaid": debt.get("is_repaid", False)
            })

    # Сортируем по дате (новые сначала)
    debts.sort(key=lambda x: x["date"], reverse=True)
    return debts


def update_debt(debt_id: int, field: str, value: Any):
    """Обновляет поле долга"""
    data = load_data()
    debt = data["debts"].get(str(debt_id))

    if debt:
        if field == "is_repaid" and value == 1:
            debt["is_repaid"] = True
            debt["repaid_at"] = datetime.now().isoformat()
        else:
            debt[field] = value
        debt["updated_at"] = datetime.now().isoformat()
        save_data(data)


def delete_debt(debt_id: int):
    """Удаляет долг"""
    data = load_data()
    if str(debt_id) in data["debts"]:
        del data["debts"][str(debt_id)]
        save_data(data)


# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---

def init_db():
    """Инициализирует базу данных"""
    data = load_data()

    # Создаем главного админа если нет
    admin_id = 8382571809  # Ваш ID
    admin_id_str = str(admin_id)

    if admin_id_str not in data["users"]:
        data["users"][admin_id_str] = {
            "user_id": admin_id,
            "role": "admin",
            "has_access": True,
            "access_until": None,
            "created_at": datetime.now().isoformat()
        }
        save_data(data)
        print("База данных инициализирована, главный админ создан")
    else:
        print("База данных загружена")