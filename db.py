# db.py
import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import requests

# --- НАСТРОЙКИ JSONBIN ---
JSONBIN_API_KEY = "ваш_api_ключ_от_jsonbin"  # Получите на jsonbin.io
MASTER_BIN_ID = "ваш_master_bin_id"  # Создайте бин и вставьте его ID
JSONBIN_BASE_URL = "https://api.jsonbin.io/v3/b"

# Структура данных для хранения в JSON
INITIAL_DATA_STRUCTURE = {
    "users": {},
    "sessions": {},
    "transactions": {},
    "debts": {}
}


class JSONBinManager:
    def __init__(self):
        self.headers = {
            "Content-Type": "application/json",
            "X-Master-Key": JSONBIN_API_KEY,
        }
        self.master_bin_id = MASTER_BIN_ID

    def _load_data(self) -> Dict[str, Any]:
        """Загружает данные из JSONBin"""
        try:
            response = requests.get(f"{JSONBIN_BASE_URL}/{self.master_bin_id}/latest", headers=self.headers)
            if response.status_code == 200:
                return response.json()["record"]
            return INITIAL_DATA_STRUCTURE.copy()
        except Exception as e:
            print(f"Ошибка загрузки данных: {e}")
            return INITIAL_DATA_STRUCTURE.copy()

    def _save_data(self, data: Dict[str, Any]) -> bool:
        """Сохраняет данные в JSONBin"""
        try:
            response = requests.put(f"{JSONBIN_BASE_URL}/{self.master_bin_id}", headers=self.headers, json=data)
            return response.status_code == 200
        except Exception as e:
            print(f"Ошибка сохранения данных: {e}")
            return False

    def _get_next_id(self, data_type: str) -> int:
        """Генерирует следующий ID для указанного типа данных"""
        data = self._load_data()
        if data_type not in data:
            return 1
        existing_ids = [int(id_) for id_ in data[data_type].keys() if id_.isdigit()]
        return max(existing_ids, default=0) + 1


# Создаем глобальный экземпляр менеджера
db_manager = JSONBinManager()


# --- ФУНКЦИИ ДЛЯ РАБОТЫ С ПОЛЬЗОВАТЕЛЯМИ ---

def ensure_user_exists(user_id: int) -> None:
    """Создает запись пользователя, если её нет"""
    data = db_manager._load_data()

    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "role": "user",
            "access_expiry": None,
            "created_at": datetime.now().isoformat()
        }
        db_manager._save_data(data)


def get_user_role(user_id: int) -> str:
    """Возвращает роль пользователя"""
    data = db_manager._load_data()
    user = data["users"].get(str(user_id), {})
    return user.get("role", "user")


def check_user_access(user_id: int) -> bool:
    """Проверяет, есть ли у пользователя доступ"""
    data = db_manager._load_data()
    user = data["users"].get(str(user_id), {})

    if user.get("role") == "admin":
        return True

    expiry_str = user.get("access_expiry")
    if not expiry_str:
        return False

    try:
        expiry = datetime.fromisoformat(expiry_str)
        return datetime.now() < expiry
    except:
        return False


def update_user_access(user_id: int, has_access: bool, days: int = 30) -> None:
    """Обновляет доступ пользователя"""
    data = db_manager._load_data()

    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "role": "user",
            "access_expiry": None,
            "created_at": datetime.now().isoformat()
        }

    if has_access:
        expiry = datetime.now() + timedelta(days=days)
        data["users"][str(user_id)]["access_expiry"] = expiry.isoformat()
    else:
        data["users"][str(user_id)]["access_expiry"] = None

    db_manager._save_data(data)


def add_admin(user_id: int) -> None:
    """Добавляет администратора"""
    data = db_manager._load_data()

    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {
            "role": "admin",
            "access_expiry": None,
            "created_at": datetime.now().isoformat()
        }
    else:
        data["users"][str(user_id)]["role"] = "admin"

    db_manager._save_data(data)


def remove_admin(user_id: int) -> None:
    """Удаляет администратора"""
    data = db_manager._load_data()

    if str(user_id) in data["users"]:
        data["users"][str(user_id)]["role"] = "user"
        data["users"][str(user_id)]["access_expiry"] = None
        db_manager._save_data(data)


def get_all_users() -> List[Dict[str, Any]]:
    """Возвращает список всех пользователей"""
    data = db_manager._load_data()
    users = []

    for user_id_str, user_data in data["users"].items():
        users.append({
            "user_id": int(user_id_str),
            "role": user_data.get("role", "user"),
            "access_expiry": user_data.get("access_expiry")
        })

    return users


def grant_access_to_all() -> None:
    """Открывает доступ всем пользователям"""
    data = db_manager._load_data()
    expiry = (datetime.now() + timedelta(days=30)).isoformat()

    for user_id_str, user_data in data["users"].items():
        if user_data.get("role") != "admin":
            data["users"][user_id_str]["access_expiry"] = expiry

    db_manager._save_data(data)


def revoke_temporary_access() -> None:
    """Закрывает доступ всем пользователям без админки"""
    data = db_manager._load_data()

    for user_id_str, user_data in data["users"].items():
        if user_data.get("role") != "admin":
            data["users"][user_id_str]["access_expiry"] = None

    db_manager._save_data(data)


# --- ФУНКЦИИ ДЛЯ РАБОТЫ С СЕССИЯМИ ---

def add_session(user_id: int, name: str, budget: float, currency: str) -> int:
    """Создает новую сессию и возвращает её ID"""
    data = db_manager._load_data()
    session_id = db_manager._get_next_id("sessions")

    data["sessions"][str(session_id)] = {
        "user_id": user_id,
        "name": name[:50],
        "budget": float(budget),
        "currency": currency,
        "is_active": True,
        "created_at": datetime.now().isoformat(),
        "closed_at": None
    }

    db_manager._save_data(data)
    return session_id


def get_user_sessions(user_id: int) -> List[tuple]:
    """Возвращает список сессий пользователя"""
    data = db_manager._load_data()
    sessions = []

    for session_id_str, session_data in data["sessions"].items():
        if session_data.get("user_id") == user_id:
            sessions.append((
                int(session_id_str),
                session_data["name"],
                session_data["budget"],
                session_data["currency"],
                session_data["is_active"]
            ))

    return sorted(sessions, key=lambda x: x[0])


def get_session_details(session_id: int) -> Optional[Dict[str, Any]]:
    """Возвращает детали сессии с расчетами"""
    data = db_manager._load_data()
    session_data = data["sessions"].get(str(session_id))

    if not session_data:
        return None

    # Получаем все транзакции для сессии
    transactions = [
        t for t in data["transactions"].values()
        if t.get("session_id") == session_id
    ]

    # Получаем все долги для сессии
    debts = [
        d for d in data["debts"].values()
        if d.get("session_id") == session_id
    ]

    # Расчеты
    sales = [t for t in transactions if t.get("type") == "sale"]
    expenses = [t for t in transactions if t.get("type") == "expense"]

    total_sales = sum(t.get("amount", 0) for t in sales)
    total_expenses = sum(t.get("expense_amount", 0) for t in sales) + sum(t.get("amount", 0) for t in expenses)

    debts_owed_to_me = [d for d in debts if d.get("type") == "owed_to_me" and not d.get("is_repaid", False)]
    debts_i_owe = [d for d in debts if d.get("type") == "i_owe" and not d.get("is_repaid", False)]

    owed_to_me = sum(d.get("amount", 0) for d in debts_owed_to_me)
    i_owe = sum(d.get("amount", 0) for d in debts_i_owe)

    balance = total_sales - total_expenses

    return {
        "name": session_data["name"],
        "currency": session_data["currency"],
        "budget": session_data["budget"],
        "is_active": session_data["is_active"],
        "balance": balance,
        "total_sales": total_sales,
        "total_expenses": total_expenses,
        "sales_count": len(sales),
        "owed_to_me": owed_to_me,
        "i_owe": i_owe
    }


def close_session(session_id: int) -> None:
    """Закрывает сессию"""
    data = db_manager._load_data()

    if str(session_id) in data["sessions"]:
        data["sessions"][str(session_id)]["is_active"] = False
        data["sessions"][str(session_id)]["closed_at"] = datetime.now().isoformat()
        db_manager._save_data(data)


# --- ФУНКЦИИ ДЛЯ ТРАНЗАКЦИЙ ---

def add_transaction(session_id: int, trans_type: str, amount: float, expense_amount: float, description: str) -> int:
    """Добавляет транзакцию (продажу или затрату)"""
    data = db_manager._load_data()
    transaction_id = db_manager._get_next_id("transactions")

    data["transactions"][str(transaction_id)] = {
        "session_id": session_id,
        "type": trans_type,
        "amount": float(amount),
        "expense_amount": float(expense_amount),
        "description": description[:100],
        "created_at": datetime.now().isoformat()
    }

    db_manager._save_data(data)
    return transaction_id


def get_transactions_list(session_id: int, trans_type: str = None, search_query: str = None) -> List[Dict[str, Any]]:
    """Возвращает список транзакций с фильтрацией"""
    data = db_manager._load_data()
    transactions = []

    for trans_id_str, trans_data in data["transactions"].items():
        if trans_data.get("session_id") != session_id:
            continue

        if trans_type and trans_data.get("type") != trans_type:
            continue

        if search_query:
            desc = trans_data.get("description", "").lower()
            if search_query.lower() not in desc:
                continue

        # Форматируем дату для отображения
        try:
            date_obj = datetime.fromisoformat(trans_data["created_at"])
            formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
        except:
            formatted_date = trans_data.get("created_at", "")

        transactions.append({
            "id": int(trans_id_str),
            "type": trans_data.get("type"),
            "amount": trans_data.get("amount", 0),
            "expense_amount": trans_data.get("expense_amount", 0),
            "description": trans_data.get("description", ""),
            "date": formatted_date
        })

    # Сортируем по дате (новые сверху)
    return sorted(transactions, key=lambda x: x.get("date", ""), reverse=True)


def update_transaction(transaction_id: int, field: str, new_value: Any) -> bool:
    """Обновляет поле транзакции"""
    data = db_manager._load_data()

    if str(transaction_id) not in data["transactions"]:
        return False

    if field in ["amount", "expense_amount"]:
        new_value = float(new_value)

    data["transactions"][str(transaction_id)][field] = new_value
    return db_manager._save_data(data)


def delete_transaction(transaction_id: int) -> bool:
    """Удаляет транзакцию"""
    data = db_manager._load_data()

    if str(transaction_id) in data["transactions"]:
        del data["transactions"][str(transaction_id)]
        return db_manager._save_data(data)

    return False


# --- ФУНКЦИИ ДЛЯ ДОЛГОВ ---

def add_debt(session_id: int, debt_type: str, person_name: str, amount: float, description: str = "") -> int:
    """Добавляет запись о долге"""
    data = db_manager._load_data()
    debt_id = db_manager._get_next_id("debts")

    data["debts"][str(debt_id)] = {
        "session_id": session_id,
        "type": debt_type,
        "person_name": person_name[:50],
        "amount": float(amount),
        "description": description[:100],
        "is_repaid": False,
        "created_at": datetime.now().isoformat()
    }

    db_manager._save_data(data)
    return debt_id


def get_debts_list(session_id: int, debt_type: str = None, search_query: str = None) -> List[Dict[str, Any]]:
    """Возвращает список долгов с фильтрацией"""
    data = db_manager._load_data()
    debts = []

    for debt_id_str, debt_data in data["debts"].items():
        if debt_data.get("session_id") != session_id:
            continue

        if debt_type and debt_data.get("type") != debt_type:
            continue

        if search_query:
            person = debt_data.get("person_name", "").lower()
            desc = debt_data.get("description", "").lower()
            if search_query.lower() not in person and search_query.lower() not in desc:
                continue

        # Форматируем дату
        try:
            date_obj = datetime.fromisoformat(debt_data["created_at"])
            formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
        except:
            formatted_date = debt_data.get("created_at", "")

        debts.append({
            "id": int(debt_id_str),
            "type": debt_data.get("type"),
            "person_name": debt_data.get("person_name", ""),
            "amount": debt_data.get("amount", 0),
            "description": debt_data.get("description", ""),
            "is_repaid": debt_data.get("is_repaid", False),
            "date": formatted_date
        })

    return sorted(debts, key=lambda x: x.get("date", ""), reverse=True)


def update_debt(debt_id: int, field: str, new_value: Any) -> bool:
    """Обновляет поле долга"""
    data = db_manager._load_data()

    if str(debt_id) not in data["debts"]:
        return False

    if field == "amount":
        new_value = float(new_value)
    elif field == "is_repaid":
        new_value = bool(int(new_value)) if isinstance(new_value, (int, str)) else bool(new_value)

    data["debts"][str(debt_id)][field] = new_value
    return db_manager._save_data(data)


def delete_debt(debt_id: int) -> bool:
    """Удаляет запись о долге"""
    data = db_manager._load_data()

    if str(debt_id) in data["debts"]:
        del data["debts"][str(debt_id)]
        return db_manager._save_data(data)

    return False


# --- ИНИЦИАЛИЗАЦИЯ ---

def init_db() -> None:
    """Инициализирует базу данных в JSONBin"""
    data = db_manager._load_data()

    # Проверяем структуру данных
    for key in INITIAL_DATA_STRUCTURE.keys():
        if key not in data:
            data[key] = INITIAL_DATA_STRUCTURE[key]

    # Добавляем главного администратора, если его нет
    if "8382571809" not in data["users"]:
        data["users"]["8382571809"] = {
            "role": "admin",
            "access_expiry": None,
            "created_at": datetime.now().isoformat()
        }

    db_manager._save_data(data)
    print("База данных инициализирована в JSONBin")