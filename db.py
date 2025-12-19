# db.py

import sqlite3
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any

# Настройка логирования для модуля
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DB_NAME = 'bot_database.db'


def _execute_query(query: str, params: tuple = (), fetch: str = None, many: bool = False) -> Optional[Any]:
    """
    Вспомогательная функция для выполнения запросов к БД.
    :param query: SQL-запрос
    :param params: Параметры для запроса
    :param fetch: Тип выборки ('one', 'all', None)
    :param many: Если True, fetchall вернет список кортежей
    :return: Результат запроса
    """
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row  # Позволяет обращаться к колонкам по имени
            cursor = conn.cursor()
            cursor.execute(query, params)
            result = None
            if fetch == 'one':
                result = cursor.fetchone()
            elif fetch == 'all':
                result = cursor.fetchall()
            conn.commit()
            return result
    except sqlite3.Error as e:
        logger.error(f"Ошибка при выполнении запроса к БД: {e}\nЗапрос: {query}\nПараметры: {params}")
        return None


def init_db() -> None:
    """Инициализирует базу данных и создает/обновляет таблицы."""
    queries = [
        '''CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            role TEXT NOT NULL DEFAULT 'user',
            has_access INTEGER NOT NULL DEFAULT 0,
            access_until TEXT,
            is_admin INTEGER NOT NULL DEFAULT 0
        )''',
        '''CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            budget REAL NOT NULL,
            currency TEXT NOT NULL,
            creation_date TEXT NOT NULL,
            is_active INTEGER NOT NULL DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )''',
        '''CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            expense_amount REAL DEFAULT 0,
            description TEXT,
            date TEXT NOT NULL,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )''',
        '''CREATE TABLE IF NOT EXISTS debts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            type TEXT NOT NULL,
            person_name TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            date TEXT NOT NULL,
            is_repaid INTEGER NOT NULL DEFAULT 0,
            FOREIGN KEY (session_id) REFERENCES sessions (id)
        )'''
    ]
    for query in queries:
        _execute_query(query)

    # Установка главного админа
    _execute_query("INSERT OR IGNORE INTO users (user_id, is_admin) VALUES (?, 1)", (8382571809,))
    logger.info("База данных инициализирована.")


def ensure_user_exists(user_id: int) -> None:
    """Гарантирует, что пользователь есть в БД. Если нет - создает."""
    _execute_query("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    logger.debug(f"Пользователь {user_id} зарегистрирован в БД.")


def get_user_role(user_id: int) -> str:
    result = _execute_query("SELECT is_admin FROM users WHERE user_id = ?", (user_id,), fetch='one')
    return 'admin' if result and result['is_admin'] else 'user'


def check_user_access(user_id: int) -> bool:
    result = _execute_query("SELECT has_access, access_until FROM users WHERE user_id = ?", (user_id,), fetch='one')
    if not result:
        return False

    has_access, access_until = result['has_access'], result['access_until']
    if has_access and not access_until:
        return True

    if has_access and access_until:
        try:
            expiry_date = datetime.strptime(access_until, '%Y-%m-%d').date()
            if datetime.now().date() <= expiry_date:
                return True
            else:
                update_user_access(user_id, False)
                return False
        except ValueError:
            logger.warning(f"Неверный формат даты access_until для пользователя {user_id}")
            return False
    return False


def update_user_access(user_id: int, grant: bool, days: int = None) -> None:
    from datetime import timedelta
    access_until = (datetime.now() + timedelta(days=days)).strftime('%Y-%m-%d') if days and grant else None
    _execute_query("UPDATE users SET has_access = ?, access_until = ? WHERE user_id = ?",
                   (int(grant), access_until, user_id))
    logger.info(f"Доступ пользователю {user_id} {'открыт' if grant else 'закрыт'}.")


def add_admin(user_id: int) -> None:
    _execute_query("UPDATE users SET is_admin = 1 WHERE user_id = ?", (user_id,))
    logger.info(f"Пользователь {user_id} назначен администратором.")


def remove_admin(user_id: int) -> None:
    _execute_query("UPDATE users SET is_admin = 0 WHERE user_id = ?", (user_id,))
    logger.info(f"Пользователь {user_id} удален из администраторов.")


def get_all_users() -> List[sqlite3.Row]:
    return _execute_query("SELECT user_id, has_access FROM users", fetch='all') or []


def add_session(user_id: int, name: str, budget: float, currency: str) -> int:
    cursor = _execute_query(
        "INSERT INTO sessions (user_id, name, budget, currency, creation_date) VALUES (?, ?, ?, ?, ?)",
        (user_id, name, budget, currency, datetime.now().strftime("%Y-%m-%d %H:%M")))
    return cursor.lastrowid if cursor else None


def get_user_sessions(user_id: int) -> List[sqlite3.Row]:
    return _execute_query(
        "SELECT id, name, budget, currency, is_active FROM sessions WHERE user_id = ? ORDER BY is_active DESC, creation_date DESC",
        (user_id,), fetch='all') or []


def get_session_details(session_id: int) -> Optional[Dict]:
    session = _execute_query("SELECT * FROM sessions WHERE id = ?", (session_id,), fetch='one')
    if not session:
        return None

    sales_data = _execute_query(
        "SELECT SUM(amount), SUM(expense_amount), COUNT(id) FROM transactions WHERE session_id = ? AND type = 'sale'",
        (session_id,), fetch='one')
    total_sales = sales_data['SUM(amount)'] or 0.0
    total_expenses_on_sales = sales_data['SUM(expense_amount)'] or 0.0
    sales_count = sales_data['COUNT(id)'] or 0

    expenses_data = _execute_query(
        "SELECT SUM(amount) FROM transactions WHERE session_id = ? AND type = 'expense'", (session_id,), fetch='one')
    total_expenses = (expenses_data['SUM(amount)'] or 0.0) + total_expenses_on_sales

    owed_to_me_data = _execute_query(
        "SELECT SUM(amount) FROM debts WHERE session_id = ? AND type = 'owed_to_me' AND is_repaid = 0",
        (session_id,), fetch='one')
    owed_to_me = owed_to_me_data['SUM(amount)'] or 0.0

    i_owe_data = _execute_query(
        "SELECT SUM(amount) FROM debts WHERE session_id = ? AND type = 'i_owe' AND is_repaid = 0",
        (session_id,), fetch='one')
    i_owe = i_owe_data['SUM(amount)'] or 0.0

    balance = total_sales - total_expenses

    return {
        "name": session['name'], "budget": session['budget'], "currency": session['currency'],
        "is_active": bool(session['is_active']), "total_sales": total_sales, "sales_count": sales_count,
        "total_expenses": total_expenses, "balance": balance, "owed_to_me": owed_to_me, "i_owe": i_owe
    }


def close_session(session_id: int) -> None:
    _execute_query("UPDATE sessions SET is_active = 0 WHERE id = ?", (session_id,))
    logger.info(f"Сессия {session_id} закрыта.")


def add_transaction(session_id: int, t_type: str, amount: float, expense_amount: float, description: str) -> int:
    cursor = _execute_query(
        "INSERT INTO transactions (session_id, type, amount, expense_amount, description, date) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, t_type, amount, expense_amount, description, datetime.now().strftime("%Y-%m-%d %H:%M")))
    return cursor.lastrowid if cursor else None


def get_transaction_by_id(trans_id: int) -> Optional[sqlite3.Row]:
    return _execute_query("SELECT * FROM transactions WHERE id = ?", (trans_id,), fetch='one')


def update_transaction(trans_id: int, field: str, value: Any) -> None:
    if field not in ['amount', 'expense_amount', 'description']:
        raise ValueError("Invalid field for update")
    _execute_query(f"UPDATE transactions SET {field} = ? WHERE id = ?", (value, trans_id))
    logger.info(f"Транзакция {trans_id} обновлена. Поле {field} = {value}")


def delete_transaction(transaction_id: int) -> None:
    _execute_query("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    logger.info(f"Транзакция {transaction_id} удалена.")


def add_debt(session_id: int, debt_type: str, person_name: str, amount: float, description: str) -> int:
    cursor = _execute_query(
        "INSERT INTO debts (session_id, type, person_name, amount, description, date) VALUES (?, ?, ?, ?, ?, ?)",
        (session_id, debt_type, person_name, amount, description, datetime.now().strftime("%Y-%m-%d %H:%M")))
    return cursor.lastrowid if cursor else None


def get_debt_by_id(debt_id: int) -> Optional[sqlite3.Row]:
    return _execute_query("SELECT * FROM debts WHERE id = ?", (debt_id,), fetch='one')


def update_debt(debt_id: int, field: str, value: Any) -> None:
    if field not in ['amount', 'person_name', 'description', 'is_repaid']:
        raise ValueError("Invalid field for update")
    _execute_query(f"UPDATE debts SET {field} = ? WHERE id = ?", (value, debt_id))
    logger.info(f"Долг {debt_id} обновлен. Поле {field} = {value}")


def delete_debt(debt_id: int) -> None:
    _execute_query("DELETE FROM debts WHERE id = ?", (debt_id,))
    logger.info(f"Долг {debt_id} удален.")


def get_transactions_list(session_id: int, t_type: str, search_query: str = None) -> List[sqlite3.Row]:
    query = "SELECT * FROM transactions WHERE session_id = ? AND type = ?"
    params = [session_id, t_type]
    if search_query:
        query += " AND description LIKE ?"
        params.append(f"%{search_query}%")
    query += " ORDER BY date DESC"
    return _execute_query(query, tuple(params), fetch='all') or []


def get_debts_list(session_id: int, debt_type: str, search_query: str = None) -> List[sqlite3.Row]:
    query = "SELECT * FROM debts WHERE session_id = ? AND type = ? AND is_repaid = 0"
    params = [session_id, debt_type]
    if search_query:
        query += " AND (person_name LIKE ? OR description LIKE ?)"
        params.extend([f"%{search_query}%", f"%{search_query}%"])
    query += " ORDER BY date DESC"
    return _execute_query(query, tuple(params), fetch='all') or []

# --- НОВЫЕ ФУНКЦИИ ДЛЯ АДМИН-ПАНЕЛИ ---

def grant_access_to_all():
    """Открывает доступ всем пользователям, у которых его не было."""
    _execute_query("UPDATE users SET has_access = 1 WHERE has_access = 0")
    logger.info("Администратор открыл доступ для всех пользователей.")

def revoke_temporary_access():
    """Закрывает доступ всем пользователям с бессрочным доступом."""
    _execute_query("UPDATE users SET has_access = 0, access_until = NULL WHERE has_access = 1 AND access_until IS NULL")
    logger.info("Администратор закрыл бессрочный доступ.")