# keyboards.py

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton
from db import load_data


# --- ГЛАВНОЕ МЕНЮ И НАВИГАЦИЯ ---

def get_main_menu_inline(sessions: list, is_admin: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_admin:
        builder.add(InlineKeyboardButton(text="🛠️ Админ-Панель", callback_data="nav_admin_panel"))
    if sessions:
        for session in sessions:
            session_id, name, budget, currency, is_active = session
            status = " (Закрыта)" if not is_active else ""
            builder.add(InlineKeyboardButton(text=f"📊 {name}/{budget}/{currency}{status}",
                                             callback_data=f"nav_session_{session_id}"))
    builder.add(InlineKeyboardButton(text="➕ Создать новую сессию", callback_data="nav_create_session"))
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_inline() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="❌ Отменить", callback_data="nav_start")]])


# --- АДМИН-ПАНЕЛЬ ---

def get_admin_panel_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👤 Управление доступом", callback_data="admin_access"))
    builder.add(InlineKeyboardButton(text="👑 Управление админами", callback_data="admin_admins"))
    builder.add(InlineKeyboardButton(text="📢 Массовая рассылка", callback_data="admin_broadcast"))
    builder.add(InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav_start"))
    builder.adjust(2)
    return builder.as_markup()


def get_access_management_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Открыть доступ пользователю", callback_data="admin_open_user"))
    builder.add(InlineKeyboardButton(text="Закрыть доступ пользователю", callback_data="admin_close_user"))
    builder.add(InlineKeyboardButton(text="Открыть доступ всем", callback_data="admin_open_all"))
    builder.add(InlineKeyboardButton(text="Закрыть доступ всем", callback_data="admin_close_all"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_admin_panel"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_management_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Добавить админа", callback_data="admin_add_admin"))
    builder.add(InlineKeyboardButton(text="Удалить админа", callback_data="admin_remove_admin"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_admin_panel"))
    builder.adjust(2)
    return builder.as_markup()


def get_broadcast_audience_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Для пользователей с доступом", callback_data="admin_broadcast_access"))
    builder.add(InlineKeyboardButton(text="Для пользователей без доступа", callback_data="admin_broadcast_no_access"))
    builder.add(InlineKeyboardButton(text="Для всех пользователей", callback_data="admin_broadcast_all"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_admin_panel"))
    builder.adjust(2)
    return builder.as_markup()


# --- МЕНЮ СЕССИИ ---

def get_session_menu_inline(is_active: bool) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if is_active:
        builder.add(InlineKeyboardButton(text="💰 Добавить продажу", callback_data="session_add_sale"))
        builder.add(InlineKeyboardButton(text="💸 Добавить затраты", callback_data="session_add_expense"))
        builder.add(InlineKeyboardButton(text="🪙 Долги", callback_data="session_manage_debts"))
        builder.add(InlineKeyboardButton(text="📈 Мои продажи", callback_data="session_list_sales"))
        builder.add(InlineKeyboardButton(text="📉 Мои затраты", callback_data="session_list_expenses"))
        builder.add(InlineKeyboardButton(text="📄 Отчет на данный момент", callback_data="session_report"))
        builder.add(InlineKeyboardButton(text="✅ Завершение сессии", callback_data="session_close_confirm"))
    else:
        builder.add(InlineKeyboardButton(text="📈 Мои продажи", callback_data="session_list_sales"))
        builder.add(InlineKeyboardButton(text="📉 Мои затраты", callback_data="session_list_expenses"))
        builder.add(InlineKeyboardButton(text="🪙 Долги", callback_data="session_manage_debts"))
        builder.add(InlineKeyboardButton(text="📄 Посмотреть отчет", callback_data="session_report"))
    builder.add(InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav_start"))
    builder.adjust(2)
    return builder.as_markup()


# --- НОВОЕ МЕНЮ УПРАВЛЕНИЯ ДОЛГАМИ ---
def get_debt_management_inline() -> InlineKeyboardMarkup:
    """Меню для выбора действия с долгами: просмотр или добавление."""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="💵 Посмотреть долги мне", callback_data="list_debts_owed_to_me"))
    builder.add(InlineKeyboardButton(text="🪙 Посмотреть мои долги", callback_data="list_debts_i_owe"))
    builder.add(InlineKeyboardButton(text="➕ Добавить долг мне", callback_data="debt_owed_to_me"))
    builder.add(InlineKeyboardButton(text="➕ Добавить мой долг", callback_data="debt_i_owe"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="session_menu"))
    builder.adjust(2)
    return builder.as_markup()


# --- СПИСКИ И ДЕЙСТВИЯ ---

def get_items_list_inline(items: list, item_type: str, session_id: int,
                          search_query: str = None) -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру для списков (транзакции, долги).
    :param items: Список объектов (строк из БД)
    :param item_type: 'transaction' или 'debt'
    :param session_id: ID текущей сессии
    :param search_query: Текущий поисковый запрос
    """
    builder = InlineKeyboardBuilder()
    for item in items:
        item_id = item['id']
        desc = item['description'] or item['person_name']
        # Обрезаем длинные названия
        short_desc = (desc[:25] + '...') if len(desc) > 25 else desc
        builder.add(InlineKeyboardButton(text=f"✏️ {short_desc}", callback_data=f"edit_{item_type}_{item_id}"))
        builder.add(InlineKeyboardButton(text="🗑️", callback_data=f"del_{item_type}_{item_id}_confirm"))
    builder.adjust(2)

    # Кнопки навигации
    nav_row = []
    if search_query:
        nav_row.append(InlineKeyboardButton(text="🔍 Изменить поиск", callback_data=f"search_{item_type}"))
    nav_row.append(InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="session_menu"))
    builder.row(*nav_row)
    return builder.as_markup()


def get_search_inline(item_type: str) -> InlineKeyboardMarkup:
    if item_type == 'debt':
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="cancel_search_debt")]
        ])
    else:
        return InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data=f"cancel_search_{item_type}")]
        ])


def get_confirmation_inline(action: str, item_id: int) -> InlineKeyboardMarkup:
    """
    action: 'del_trans', 'del_debt', 'close_session'
    """
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="✅ Да, уверен", callback_data=f"confirm_{action}_{item_id}"))
    builder.add(InlineKeyboardButton(text="❌ Нет, отмена", callback_data="cancel_action"))
    builder.adjust(2)
    return builder.as_markup()


def get_edit_item_inline(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    """Создает клавиатуру для редактирования элемента"""
    builder = InlineKeyboardBuilder()

    if item_type == 'transaction':
        # Узнаем тип транзакции (sale или expense)
        data = load_data()
        trans = data.get("transactions", {}).get(str(item_id))

        if trans:
            trans_type = trans.get("type", "sale")

            if trans_type == "sale":
                # Для продаж: сумма, затраты, описание
                builder.add(InlineKeyboardButton(text="Сумма продажи",
                                                 callback_data=f"edit_field_{item_type}_{item_id}_amount"))
                builder.add(InlineKeyboardButton(text="Затраты",
                                                 callback_data=f"edit_field_{item_type}_{item_id}_expense_amount"))
                builder.add(InlineKeyboardButton(text="Описание",
                                                 callback_data=f"edit_field_{item_type}_{item_id}_description"))
            elif trans_type == "expense":
                # Для затрат: только сумма и описание (без затрат)
                builder.add(
                    InlineKeyboardButton(text="Сумма затрат", callback_data=f"edit_field_{item_type}_{item_id}_amount"))
                builder.add(InlineKeyboardButton(text="Описание",
                                                 callback_data=f"edit_field_{item_type}_{item_id}_description"))
        else:
            # Если не удалось определить тип, показываем общие кнопки
            builder.add(InlineKeyboardButton(text="Сумма", callback_data=f"edit_field_{item_type}_{item_id}_amount"))
            builder.add(
                InlineKeyboardButton(text="Затраты", callback_data=f"edit_field_{item_type}_{item_id}_expense_amount"))
            builder.add(
                InlineKeyboardButton(text="Описание", callback_data=f"edit_field_{item_type}_{item_id}_description"))

    elif item_type == 'debt':
        builder.add(InlineKeyboardButton(text="Сумма", callback_data=f"edit_field_{item_type}_{item_id}_amount"))
        builder.add(InlineKeyboardButton(text="Имя", callback_data=f"edit_field_{item_type}_{item_id}_person_name"))
        builder.add(
            InlineKeyboardButton(text="Описание", callback_data=f"edit_field_{item_type}_{item_id}_description"))
        builder.add(InlineKeyboardButton(text="Погашен", callback_data=f"repay_debt_{item_id}"))

    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data=f"cancel_edit_{item_type}"))

    # Настраиваем количество кнопок в ряду
    if item_type == 'transaction':
        # Проверяем тип транзакции для правильного расположения кнопок
        if 'data' in locals() and trans and trans.get("type") == "expense":
            builder.adjust(2, 1)  # 2 кнопки в первом ряду, 1 во втором
        else:
            builder.adjust(2, 1, 1)  # 2 кнопки в первом ряду, 1 во втором, 1 в третьем
    else:
        builder.adjust(2, 2, 1)  # Для долгов: 2, 2, 1

    return builder.as_markup()


def get_currency_inline() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="USDT", callback_data="currency_USDT"))
    builder.add(InlineKeyboardButton(text="Рубль ПМР", callback_data="currency_RUB"))
    return builder.as_markup()