# db.py - полная исправленная версия

import json
import requests
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
import time
import logging

logger = logging.getLogger(__name__)

# --- НАСТРОЙКИ JSONBIN.IO ---
MASTER_BIN_ID = "$2a$10$eCHhQtmSAhD8XqkrlFgE1O6N6OKwgmHrIg"  # ЗАМЕНИТЕ НА ВАШ
JSONBIN_API_KEY = "694818b2d0ea881f40380c8c"  # ЗАМЕНИТЕ НА ВАШ

API_URL = "https://api.jsonbin.io/v3/b"
HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_API_KEY,
    "X-Bin-Meta": "false"
}

# --- КЭШИРОВАНИЕ ---
_CACHE = {}
_CACHE_TIMESTAMP = {}
_CACHE_TTL = 3  # Кэш на 3 секунды

# В начало db.py добавьте:
EMERGENCY_ADMIN_MODE = True  # Поставьте True для принудительного включения админа


# Исправьте check_user_access:
def check_user_access(user_id: int) -> bool:
    """Проверяет доступ пользователя - с аварийным режимом"""
    if EMERGENCY_ADMIN_MODE and user_id == 8382571809:
        print(f"⚡ АВАРИЙНЫЙ РЕЖИМ: Принудительно даем доступ админу {user_id}")
        return True

    data = load_data_cached()
    user = data.get("users", {}).get(str(user_id))

    if not user:
        return False

    # Всегда даем доступ админу
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
def clear_cache(cache_key: str = None):
    """Очищает кэш полностью или для конкретного ключа"""
    global _CACHE, _CACHE_TIMESTAMP

    if cache_key:
        if cache_key in _CACHE:
            del _CACHE[cache_key]
        if cache_key in _CACHE_TIMESTAMP:
            del _CACHE_TIMESTAMP[cache_key]
        logger.debug(f"Кэш очищен для ключа: {cache_key}")
    else:
        _CACHE.clear()
        _CACHE_TIMESTAMP.clear()
        logger.debug("Весь кэш очищен")


def load_data_cached(force_refresh: bool = False) -> dict:
    """Загружает данные с кэшированием"""
    global _CACHE, _CACHE_TIMESTAMP

    cache_key = "main_data"
    current_time = time.time()

    # Принудительное обновление или кэш устарел
    if (force_refresh or
            cache_key not in _CACHE or
            current_time - _CACHE_TIMESTAMP.get(cache_key, 0) > _CACHE_TTL):
        data = _load_data_raw()
        _CACHE[cache_key] = data
        _CACHE_TIMESTAMP[cache_key] = current_time
        logger.debug(f"Данные загружены из JSONBin (force: {force_refresh})")
        return data

    logger.debug("Используются кэшированные данные")
    return _CACHE[cache_key]


def _load_data_raw() -> dict:
    """Загружает сырые данные из JSONBin"""
    try:
        response = requests.get(f"{API_URL}/{MASTER_BIN_ID}", headers=HEADERS, timeout=10)
        response.raise_for_status()
        data = response.json()

        # Проверяем структуру
        if not data or not isinstance(data, dict):
            logger.warning("Получены пустые данные, создаем структуру")
            return _create_empty_structure()

        # Убедимся что все ключи существуют
        required_keys = ["users", "sessions", "transactions", "debts", "counters"]
        for key in required_keys:
            if key not in data:
                logger.warning(f"Ключ '{key}' отсутствует, создаем")
                if key == "counters":
                    data[key] = {"session_id": 0, "transaction_id": 0, "debt_id": 0}
                else:
                    data[key] = {}

        return data

    except requests.exceptions.RequestException as e:
        logger.error(f"Ошибка сети при загрузке данных: {e}")
        return _create_empty_structure()
    except Exception as e:
        logger.error(f"Неизвестная ошибка при загрузке данных: {e}")
        return _create_empty_structure()


def _create_empty_structure() -> dict:
    """Создает пустую структуру данных"""
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


def save_data(data: dict) -> bool:
    """Сохраняет данные в JSONBin и очищает кэш"""
    try:
        response = requests.put(f"{API_URL}/{MASTER_BIN_ID}",
                                json=data,
                                headers=HEADERS,
                                timeout=10)
        response.raise_for_status()

        # ОЧИЩАЕМ КЭШ ПОСЛЕ СОХРАНЕНИЯ - ЭТО ВАЖНО!
        clear_cache()
        logger.debug("Данные сохранены и кэш очищен")
        return True

    except Exception as e:
        logger.error(f"Ошибка сохранения данных: {e}")
        return False


def get_next_id(counter_name: str) -> int:
    """Получает следующий ID"""
    data = load_data_cached(force_refresh=True)  # Всегда свежие данные для счетчиков
    data["counters"][counter_name] += 1

    if save_data(data):
        return data["counters"][counter_name]
    return 0


# --- ФУНКЦИИ ДЛЯ ПОЛЬЗОВАТЕЛЕЙ ---

def ensure_user_exists(user_id: int):
    """Создает пользователя если не существует"""
    data = load_data_cached(force_refresh=True)
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
    data = load_data_cached()
    user = data.get("users", {}).get(str(user_id))
    if user:
        # Обрабатываем оба формата: число или строку
        stored_id = user.get("user_id")
        if isinstance(stored_id, str):
            try:
                stored_id = int(stored_id)
            except ValueError:
                return "user"

        if stored_id == user_id:
            return user.get("role", "user")
    return "user"


def check_user_access(user_id: int) -> bool:
    """Проверяет доступ пользователя"""
    data = load_data_cached()
    user = data.get("users", {}).get(str(user_id))

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
    data = load_data_cached(force_refresh=True)
    user_id_str = str(user_id)

    if user_id_str not in data["users"]:
        ensure_user_exists(user_id)
        data = load_data_cached(force_refresh=True)  # Перезагружаем

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
    data = load_data_cached()
    return list(data.get("users", {}).values())


def add_admin(user_id: int):
    """Добавляет администратора"""
    data = load_data_cached(force_refresh=True)
    user_id_str = str(user_id)

    if user_id_str not in data["users"]:
        ensure_user_exists(user_id)
        data = load_data_cached(force_refresh=True)

    data["users"][user_id_str]["role"] = "admin"
    data["users"][user_id_str]["has_access"] = True
    save_data(data)


def remove_admin(user_id: int):
    """Удаляет администратора"""
    data = load_data_cached(force_refresh=True)
    user_id_str = str(user_id)

    if user_id_str in data["users"]:
        data["users"][user_id_str]["role"] = "user"
        save_data(data)


def grant_access_to_all():
    """Дает доступ всем пользователям"""
    data = load_data_cached(force_refresh=True)
    for user_id, user_data in data.get("users", {}).items():
        user_data["has_access"] = True
    save_data(data)


def revoke_temporary_access():
    """Отзывает доступ у неоплативших пользователей"""
    data = load_data_cached(force_refresh=True)
    for user_id, user_data in data.get("users", {}).items():
        if user_data.get("role") != "admin":
            user_data["has_access"] = False
            user_data["access_until"] = None
    save_data(data)


# --- ФУНКЦИИ ДЛЯ СЕССИЙ ---

def add_session(user_id: int, name: str, budget: float, currency: str) -> int:
    """Добавляет новую сессию"""
    data = load_data_cached(force_refresh=True)

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

    if save_data(data):
        logger.info(f"Сессия '{name}' создана (ID: {session_id})")
        return session_id
    return 0


def get_user_sessions(user_id: int) -> List[tuple]:
    """Получает сессии пользователя"""
    data = load_data_cached()
    sessions = []

    for session in data.get("sessions", {}).values():
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
    return sessions


def get_session_details(session_id: int) -> Optional[Dict]:
    """Получает детали сессии с расчетами"""
    data = load_data_cached()
    session = data.get("sessions", {}).get(str(session_id))

    if not session:
        return None

    # Рассчитываем статистику
    total_sales = 0
    total_expenses = 0
    sales_count = 0
    owed_to_me = 0
    i_owe = 0

    # Считаем транзакции
    for trans in data.get("transactions", {}).values():
        if trans["session_id"] == session_id:
            if trans["type"] == "sale":
                total_sales += trans["amount"]
                total_expenses += trans.get("expense_amount", 0)
                sales_count += 1
            elif trans["type"] == "expense":
                total_expenses += trans["amount"]

    # Считаем долги
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
    data = load_data_cached(force_refresh=True)
    session = data.get("sessions", {}).get(str(session_id))

    if session:
        session["is_active"] = False
        session["closed_at"] = datetime.now().isoformat()
        save_data(data)


# --- ФУНКЦИИ ДЛЯ ТРАНЗАКЦИЙ ---

def add_transaction(session_id: int, trans_type: str, amount: float,
                    expense_amount: float = 0, description: str = "") -> int:
    """Добавляет транзакцию"""
    data = load_data_cached(force_refresh=True)

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

    if save_data(data):
        return transaction_id
    return 0


def get_transactions_list(session_id: int, trans_type: str,
                          search_query: str = None) -> List[Dict]:
    """Получает список транзакций"""
    data = load_data_cached()
    transactions = []

    for trans in data.get("transactions", {}).values():
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
    data = load_data_cached(force_refresh=True)
    trans = data.get("transactions", {}).get(str(trans_id))

    if trans:
        trans[field] = value
        trans["updated_at"] = datetime.now().isoformat()
        save_data(data)


def delete_transaction(trans_id: int):
    """Удаляет транзакцию"""
    data = load_data_cached(force_refresh=True)
    if str(trans_id) in data.get("transactions", {}):
        del data["transactions"][str(trans_id)]
        save_data(data)


# --- ФУНКЦИИ ДЛЯ ДОЛГОВ ---

def add_debt(session_id: int, debt_type: str, person_name: str,
             amount: float, description: str = "") -> int:
    """Добавляет долг"""
    data = load_data_cached(force_refresh=True)

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

    if save_data(data):
        return debt_id
    return 0


def get_debts_list(session_id: int, debt_type: str,
                   search_query: str = None) -> List[Dict]:
    """Получает список долгов"""
    data = load_data_cached()
    debts = []

    for debt in data.get("debts", {}).values():
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
    data = load_data_cached(force_refresh=True)
    debt = data.get("debts", {}).get(str(debt_id))

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
    data = load_data_cached(force_refresh=True)
    if str(debt_id) in data.get("debts", {}):
        del data["debts"][str(debt_id)]
        save_data(data)


# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ---

def init_db():
    """Инициализирует базу данных"""
    logger.info("Инициализация базы данных...")

    data = load_data_cached(force_refresh=True)

    # Создаем главного админа если нет
    admin_id = 8382571809
    admin_id_str = str(admin_id)

    if admin_id_str not in data.get("users", {}):
        logger.info("Админ не найден, создаем...")
        data.setdefault("users", {})[admin_id_str] = {
            "user_id": admin_id,
            "role": "admin",
            "has_access": True,
            "access_until": None,
            "created_at": datetime.now().isoformat()
        }
        save_data(data)
        logger.info("Главный админ создан")
    else:
        admin_data = data["users"][admin_id_str]
        logger.info(f"Админ найден: роль={admin_data.get('role')}")

        # Исправляем если что-то не так
        if admin_data.get('role') != 'admin':
            admin_data['role'] = 'admin'
            admin_data['has_access'] = True
            save_data(data)
            logger.info("Роль админа исправлена")

    logger.info("Инициализация завершена")
    return True


# --- ОБРАТНАЯ СОВМЕСТИМОСТЬ ---
def load_data() -> dict:
    """Алиас для обратной совместимости (используется в keyboards.py)"""
    import warnings
    warnings.warn("load_data() устарела, используйте load_data_cached()", DeprecationWarning)
    return load_data_cached()