# db_fixed.py - ПОЛНОСТЬЮ ИСПРАВЛЕННАЯ ВЕРСИЯ

import json
import os
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import logging

logger = logging.getLogger(__name__)

# Файл для хранения данных
DB_FILE = "bot_data.json"


# --- ОСНОВНЫЕ ФУНКЦИИ С ПРИНУДИТЕЛЬНОЙ ПЕРЕЗАГРУЗКОЙ ---

def _load_data_force() -> dict:
    """Загружает данные из файла - ВСЕГДА С ДИСКА"""
    if not os.path.exists(DB_FILE):
        return _create_empty_structure()

    try:
        with open(DB_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            logger.debug(f"📥 Загружено с диска, сессий: {len(data.get('sessions', {}))}")
            return data
    except Exception as e:
        logger.error(f"❌ Ошибка загрузки: {e}")
        return _create_empty_structure()


def _save_data_force(data: dict) -> bool:
    """Сохраняет данные в файл - ВСЕГДА НА ДИСК"""
    try:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.debug(f"💾 Сохранено на диск")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения: {e}")
        return False


def _create_empty_structure() -> dict:
    """Создает пустую структуру данных"""
    return {
        "users": {
            "8382571809": {
                "user_id": 8382571809,
                "role": "admin",
                "has_access": True,
                "access_until": None,
                "created_at": datetime.now().isoformat()
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


# --- ФУНКЦИИ ДЛЯ СЕССИЙ (ВСЕГДА С ДИСКА) ---

def _get_and_increment_counter(counter_name: str) -> int:
    """Получает и увеличивает счетчик - атомарная операция"""
    data = _load_data_force()
    current = data["counters"][counter_name]
    new_value = current + 1
    data["counters"][counter_name] = new_value
    _save_data_force(data)
    logger.info(f"🔢 Счетчик {counter_name}: {current} -> {new_value}")
    return new_value


def add_session(user_id: int, name: str, budget: float, currency: str) -> int:
    """Добавляет новую сессию"""
    # 1. Получаем новый ID
    session_id = _get_and_increment_counter("session_id")

    # 2. Загружаем ВСЕ данные
    data = _load_data_force()

    # 3. Создаем новую сессию
    new_session = {
        "id": session_id,
        "user_id": user_id,
        "name": name[:50],
        "budget": budget,
        "currency": currency,
        "is_active": True,
        "created_at": datetime.now().isoformat()
    }

    # 4. Добавляем сессию
    data["sessions"][str(session_id)] = new_session

    # 5. Сохраняем ВСЕ данные
    if _save_data_force(data):
        # Логируем результат
        logger.info(f"✅ Сессия создана: ID={session_id}, Имя='{name}'")
        logger.info(f"📊 Всего сессий теперь: {len(data['sessions'])}")

        # Выводим все сессии для отладки
        for sid, sess in data["sessions"].items():
            logger.info(f"   Сессия {sid}: ID={sess['id']}, Имя='{sess['name']}', Пользователь={sess['user_id']}")

        return session_id

    logger.error("❌ Не удалось сохранить сессию")
    return 0


def get_user_sessions(user_id: int) -> List[tuple]:
    """Получает сессии пользователя"""
    # ВСЕГДА загружаем с диска
    data = _load_data_force()
    sessions = []

    logger.info(f"🔍 Поиск сессий для пользователя {user_id}")
    logger.info(f"📊 Всего сессий в файле: {len(data.get('sessions', {}))}")

    for session_id_str, session in data.get("sessions", {}).items():
        logger.info(f"   Проверяем сессию {session_id_str}: пользователь={session['user_id']}, имя='{session['name']}'")

        if session["user_id"] == user_id:
            sessions.append((
                session["id"],
                session["name"],
                session["budget"],
                session["currency"],
                session["is_active"]
            ))

    # Сортируем по ID (новые сначала)
    sessions.sort(key=lambda x: x[0], reverse=True)
    logger.info(f"📋 Найдено сессий: {len(sessions)}")

    return sessions


def get_session_details(session_id: int) -> Optional[Dict]:
    """Получает детали сессии"""
    data = _load_data_force()
    session = data.get("sessions", {}).get(str(session_id))

    if not session:
        return None

    # Расчеты остаются прежними
    total_sales = 0
    total_expenses = 0
    sales_count = 0
    owed_to_me = 0
    i_owe = 0

    for trans in data.get("transactions", {}).values():
        if trans["session_id"] == session_id:
            if trans["type"] == "sale":
                total_sales += trans["amount"]
                total_expenses += trans.get("expense_amount", 0)
                sales_count += 1
            elif trans["type"] == "expense":
                total_expenses += trans["amount"]

    for debt in data.get("debts", {}).values():
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
    data = _load_data_force()
    session = data.get("sessions", {}).get(str(session_id))

    if session:
        session["is_active"] = False
        session["closed_at"] = datetime.now().isoformat()
        _save_data_force(data)


# --- ОСТАЛЬНЫЕ ФУНКЦИИ (упрощенные) ---

def add_transaction(session_id: int, trans_type: str, amount: float,
                    expense_amount: float = 0, description: str = "") -> int:
    """Добавляет транзакцию"""
    transaction_id = _get_and_increment_counter("transaction_id")
    data = _load_data_force()

    data["transactions"][str(transaction_id)] = {
        "id": transaction_id,
        "session_id": session_id,
        "type": trans_type,
        "amount": amount,
        "expense_amount": expense_amount if trans_type == "sale" else 0,
        "description": description[:100],
        "date": datetime.now().isoformat()
    }

    _save_data_force(data)
    return transaction_id


def add_debt(session_id: int, debt_type: str, person_name: str,
             amount: float, description: str = "") -> int:
    """Добавляет долг"""
    debt_id = _get_and_increment_counter("debt_id")
    data = _load_data_force()

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

    _save_data_force(data)
    return debt_id


def get_user_role(user_id: int) -> str:
    """Получает роль пользователя"""
    if user_id == 8382571809:
        return "admin"

    data = _load_data_force()
    user = data.get("users", {}).get(str(user_id))
    return user.get("role", "user") if user else "user"


def check_user_access(user_id: int) -> bool:
    """Проверяет доступ пользователя"""
    if user_id == 8382571809:
        return True

    data = _load_data_force()
    user = data.get("users", {}).get(str(user_id))

    if not user:
        return False

    if user.get("role") == "admin":
        return True

    return user.get("has_access", False)


# --- ОСТАЛЬНЫЕ ФУНКЦИИ (просто обертки) ---

def update_transaction(trans_id: int, field: str, value: Any):
    data = _load_data_force()
    trans = data.get("transactions", {}).get(str(trans_id))
    if trans:
        trans[field] = value
        _save_data_force(data)


def delete_transaction(trans_id: int):
    data = _load_data_force()
    if str(trans_id) in data.get("transactions", {}):
        del data["transactions"][str(trans_id)]
        _save_data_force(data)


def update_debt(debt_id: int, field: str, value: Any):
    data = _load_data_force()
    debt = data.get("debts", {}).get(str(debt_id))
    if debt:
        if field == "is_repaid" and value == 1:
            debt["is_repaid"] = True
        else:
            debt[field] = value
        _save_data_force(data)


def delete_debt(debt_id: int):
    data = _load_data_force()
    if str(debt_id) in data.get("debts", {}):
        del data["debts"][str(debt_id)]
        _save_data_force(data)


def get_transactions_list(session_id: int, trans_type: str, search_query: str = None) -> List[Dict]:
    data = _load_data_force()
    transactions = []

    for trans in data.get("transactions", {}).values():
        if trans["session_id"] == session_id and trans["type"] == trans_type:
            if search_query and search_query.lower() not in trans["description"].lower():
                continue

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

    transactions.sort(key=lambda x: x["date"], reverse=True)
    return transactions


def get_debts_list(session_id: int, debt_type: str, search_query: str = None) -> List[Dict]:
    data = _load_data_force()
    debts = []

    for debt in data.get("debts", {}).values():
        if debt["session_id"] == session_id and debt["type"] == debt_type:
            if search_query:
                if (search_query.lower() not in debt["person_name"].lower() and
                        search_query.lower() not in debt["description"].lower()):
                    continue

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

    debts.sort(key=lambda x: x["date"], reverse=True)
    return debts


def ensure_user_exists(user_id: int):
    data = _load_data_force()
    user_id_str = str(user_id)

    if user_id_str not in data["users"]:
        data["users"][user_id_str] = {
            "user_id": user_id,
            "role": "user",
            "has_access": False,
            "access_until": None,
            "created_at": datetime.now().isoformat()
        }
        _save_data_force(data)


def update_user_access(user_id: int, grant_access: bool, days: int = 0):
    data = _load_data_force()
    user_id_str = str(user_id)

    if user_id_str not in data["users"]:
        ensure_user_exists(user_id)
        data = _load_data_force()

    user = data["users"][user_id_str]
    user["has_access"] = grant_access

    if grant_access and days > 0:
        until_date = datetime.now() + timedelta(days=days)
        user["access_until"] = until_date.isoformat()
    else:
        user["access_until"] = None

    _save_data_force(data)


def get_all_users() -> List[Dict]:
    data = _load_data_force()
    return list(data.get("users", {}).values())


def add_admin(user_id: int):
    data = _load_data_force()
    user_id_str = str(user_id)

    if user_id_str not in data["users"]:
        ensure_user_exists(user_id)
        data = _load_data_force()

    data["users"][user_id_str]["role"] = "admin"
    data["users"][user_id_str]["has_access"] = True
    _save_data_force(data)


def remove_admin(user_id: int):
    data = _load_data_force()
    user_id_str = str(user_id)

    if user_id_str in data["users"]:
        data["users"][user_id_str]["role"] = "user"
        _save_data_force(data)


def grant_access_to_all():
    data = _load_data_force()
    for user_data in data.get("users", {}).values():
        user_data["has_access"] = True
    _save_data_force(data)


def revoke_temporary_access():
    data = _load_data_force()
    for user_data in data.get("users", {}).values():
        if user_data.get("role") != "admin":
            user_data["has_access"] = False
            user_data["access_until"] = None
    _save_data_force(data)


# --- ИНИЦИАЛИЗАЦИЯ ---

def init_db():
    """Инициализирует базу данных"""
    logger.info("Инициализация базы данных...")

    # Просто создаем файл если его нет
    if not os.path.exists(DB_FILE):
        data = _create_empty_structure()
        _save_data_force(data)
        logger.info("✅ Файл базы данных создан")

    logger.info("✅ База данных готова")
    return True