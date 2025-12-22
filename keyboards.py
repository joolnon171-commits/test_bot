# keyboards.py

from aiogram.utils.keyboard import InlineKeyboardBuilder, InlineKeyboardMarkup
from aiogram.types import InlineKeyboardButton


# --- ГЛАВНОЕ МЕНЮ И НАВИГАЦИЯ ---

def get_main_menu_inline(sessions: list, is_admin: bool) -> InlineKeyboardMarkup:
    """
    Генерирует главное меню.
    :param sessions: Список сессий пользователя в формате (id, name, budget, currency, is_active)
    :param is_admin: Является ли пользователь администратором
    """
    builder = InlineKeyboardBuilder()

    if is_admin:
        builder.add(InlineKeyboardButton(text="🛠️ Админ-Панель", callback_data="nav_admin_panel"))

    if sessions:
        for session in sessions:
            session_id, name, budget, currency, is_active = session
            # Обрезаем длинное название
            short_name = (name[:15] + '...') if len(name) > 15 else name
            status_icon = "✅" if is_active else "❌"
            builder.add(InlineKeyboardButton(
                text=f"{status_icon} {short_name} ({budget:.0f} {currency})",
                callback_data=f"nav_session_{session_id}"
            ))

    builder.add(InlineKeyboardButton(text="➕ Создать новую сессию", callback_data="nav_create_session"))
    builder.adjust(1)
    return builder.as_markup()


def get_cancel_inline() -> InlineKeyboardMarkup:
    """Клавиатура для отмены действия"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data="nav_start")]
    ])


# --- АДМИН-ПАНЕЛЬ ---

def get_admin_panel_inline() -> InlineKeyboardMarkup:
    """Клавиатура админ-панели"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="👤 Управление доступом", callback_data="admin_access"))
    builder.add(InlineKeyboardButton(text="👑 Управление админами", callback_data="admin_admins"))
    builder.add(InlineKeyboardButton(text="📢 Массовая рассылка", callback_data="admin_broadcast"))
    builder.add(InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav_start"))
    builder.adjust(2)
    return builder.as_markup()


def get_access_management_inline() -> InlineKeyboardMarkup:
    """Клавиатура управления доступом"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Открыть доступ пользователю", callback_data="admin_open_user"))
    builder.add(InlineKeyboardButton(text="Закрыть доступ пользователю", callback_data="admin_close_user"))
    builder.add(InlineKeyboardButton(text="Открыть доступ всем", callback_data="admin_open_all"))
    builder.add(InlineKeyboardButton(text="Закрыть доступ всем", callback_data="admin_close_all"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_admin_panel"))
    builder.adjust(2)
    return builder.as_markup()


def get_admin_management_inline() -> InlineKeyboardMarkup:
    """Клавиатура управления администраторами"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Добавить админа", callback_data="admin_add_admin"))
    builder.add(InlineKeyboardButton(text="Удалить админа", callback_data="admin_remove_admin"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_admin_panel"))
    builder.adjust(2)
    return builder.as_markup()


def get_broadcast_audience_inline() -> InlineKeyboardMarkup:
    """Клавиатура выбора аудитории для рассылки"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Для пользователей с доступом", callback_data="admin_broadcast_access"))
    builder.add(InlineKeyboardButton(text="Для пользователей без доступа", callback_data="admin_broadcast_no_access"))
    builder.add(InlineKeyboardButton(text="Для всех пользователей", callback_data="admin_broadcast_all"))
    builder.add(InlineKeyboardButton(text="⬅️ Назад", callback_data="nav_admin_panel"))
    builder.adjust(2)
    return builder.as_markup()


# --- МЕНЮ СЕССИИ ---

def get_session_menu_inline(is_active: bool) -> InlineKeyboardMarkup:
    """
    Генерирует меню сессии.
    :param is_active: Активна ли сессия
    """
    builder = InlineKeyboardBuilder()

    if is_active:
        # Операции доступные только для активных сессий
        builder.add(InlineKeyboardButton(text="💰 Добавить продажу", callback_data="session_add_sale"))
        builder.add(InlineKeyboardButton(text="💸 Добавить затраты", callback_data="session_add_expense"))
        builder.add(InlineKeyboardButton(text="🪙 Долги", callback_data="session_manage_debts"))
        builder.add(InlineKeyboardButton(text="📈 Мои продажи", callback_data="session_list_sales"))
        builder.add(InlineKeyboardButton(text="📉 Мои затраты", callback_data="session_list_expenses"))
        builder.add(InlineKeyboardButton(text="📄 Отчет на данный момент", callback_data="session_report"))
        builder.add(InlineKeyboardButton(text="✅ Завершение сессии", callback_data="session_close_confirm"))
    else:
        # Только просмотр для закрытых сессий
        builder.add(InlineKeyboardButton(text="📈 Мои продажи", callback_data="session_list_sales"))
        builder.add(InlineKeyboardButton(text="📉 Мои затраты", callback_data="session_list_expenses"))
        builder.add(InlineKeyboardButton(text="🪙 Долги", callback_data="session_manage_debts"))
        builder.add(InlineKeyboardButton(text="📄 Посмотреть отчет", callback_data="session_report"))

    builder.add(InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav_start"))
    builder.adjust(2)
    return builder.as_markup()


# --- УПРАВЛЕНИЕ ДОЛГАМИ ---

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
    :param items: Список объектов из БД
    :param item_type: 'transaction' или 'debt'
    :param session_id: ID текущей сессии
    :param search_query: Текущий поисковый запрос
    """
    builder = InlineKeyboardBuilder()

    for item in items:
        item_id = item['id']

        # Формируем текст для кнопки
        if item_type == 'transaction':
            # Для транзакций показываем описание
            desc = item.get('description', 'Без названия')
            short_desc = (desc[:20] + '...') if len(desc) > 20 else desc

            # Добавляем значки для типа транзакции
            icon = "💰" if item.get('type') == 'sale' else "💸"
            button_text = f"{icon} {short_desc}"

        elif item_type == 'debt':
            # Для долгов показываем имя и статус
            person_name = item.get('person_name', 'Без имени')
            short_name = (person_name[:20] + '...') if len(person_name) > 20 else person_name

            # Добавляем иконку в зависимости от типа долга и статуса
            if item.get('type') == 'owed_to_me':
                icon = "💵"
            else:
                icon = "🪙"

            # Отмечаем погашенные долги
            if item.get('is_repaid', False):
                icon = "✅"

            button_text = f"{icon} {short_name}"

        # Добавляем кнопки редактирования и удаления
        builder.add(InlineKeyboardButton(
            text=button_text,
            callback_data=f"edit_{item_type}_{item_id}"
        ))
        builder.add(InlineKeyboardButton(
            text="🗑️",
            callback_data=f"del_{item_type}_{item_id}_confirm"
        ))

    builder.adjust(2)

    # Кнопки навигации
    nav_buttons = []

    # Кнопка поиска
    if search_query:
        nav_buttons.append(InlineKeyboardButton(
            text="🔍 Изменить поиск",
            callback_data=f"search_{'debt' if item_type == 'debt' else 'transaction'}"
        ))

    # Кнопка возврата в меню
    nav_buttons.append(InlineKeyboardButton(
        text="⬅️ Назад в меню",
        callback_data="session_menu"
    ))

    builder.row(*nav_buttons)
    return builder.as_markup()


def get_search_inline(item_type: str) -> InlineKeyboardMarkup:
    """Клавиатура для поиска"""
    cancel_action = f"cancel_search_{item_type}"

    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="❌ Отменить", callback_data=cancel_action)]
    ])


def get_confirmation_inline(action: str, item_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура подтверждения действий.
    :param action: 'del_transaction', 'del_debt', 'close_session'
    :param item_id: ID элемента
    """
    builder = InlineKeyboardBuilder()

    if action == 'close_session':
        confirm_text = "✅ Да, завершить сессию"
    else:
        confirm_text = "✅ Да, удалить"

    builder.add(InlineKeyboardButton(
        text=confirm_text,
        callback_data=f"confirm_{action}_{item_id}"
    ))
    builder.add(InlineKeyboardButton(
        text="❌ Нет, отмена",
        callback_data="cancel_action"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_edit_item_inline(item_type: str, item_id: int) -> InlineKeyboardMarkup:
    """
    Клавиатура для выбора поля редактирования.
    :param item_type: 'transaction' или 'debt'
    :param item_id: ID элемента
    """
    builder = InlineKeyboardBuilder()

    if item_type == 'transaction':
        builder.add(InlineKeyboardButton(
            text="✏️ Сумма",
            callback_data=f"edit_field_{item_type}_{item_id}_amount"
        ))
        builder.add(InlineKeyboardButton(
            text="✏️ Затраты",
            callback_data=f"edit_field_{item_type}_{item_id}_expense_amount"
        ))
        builder.add(InlineKeyboardButton(
            text="✏️ Описание",
            callback_data=f"edit_field_{item_type}_{item_id}_description"
        ))

    elif item_type == 'debt':
        builder.add(InlineKeyboardButton(
            text="✏️ Сумма",
            callback_data=f"edit_field_{item_type}_{item_id}_amount"
        ))
        builder.add(InlineKeyboardButton(
            text="✏️ Имя",
            callback_data=f"edit_field_{item_type}_{item_id}_person_name"
        ))
        builder.add(InlineKeyboardButton(
            text="✏️ Описание",
            callback_data=f"edit_field_{item_type}_{item_id}_description"
        ))
        builder.add(InlineKeyboardButton(
            text="✅ Погашен",
            callback_data=f"repay_debt_{item_id}"
        ))

    builder.add(InlineKeyboardButton(
        text="⬅️ Назад",
        callback_data=f"cancel_edit_{item_type}"
    ))

    builder.adjust(2)
    return builder.as_markup()


def get_currency_inline() -> InlineKeyboardMarkup:
    """Клавиатура выбора валюты"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="USDT", callback_data="currency_USDT"))
    builder.add(InlineKeyboardButton(text="Рубль ПМР", callback_data="currency_RUB"))
    builder.adjust(2)
    return builder.as_markup()


# --- ДОПОЛНИТЕЛЬНЫЕ КЛАВИАТУРЫ ---

def get_back_to_session_menu_inline(session_id: int) -> InlineKeyboardMarkup:
    """Простая кнопка возврата в меню сессии"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В меню", callback_data=f"nav_session_{session_id}")]
    ])


def get_back_to_main_menu_inline() -> InlineKeyboardMarkup:
    """Простая кнопка возврата в главное меню"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ В главное меню", callback_data="nav_start")]
    ])


def get_pagination_inline(page: int, total_pages: int, callback_prefix: str,
                          extra_data: str = "") -> InlineKeyboardMarkup:
    """
    Генерирует клавиатуру пагинации.
    :param page: Текущая страница
    :param total_pages: Всего страниц
    :param callback_prefix: Префикс для callback данных
    :param extra_data: Дополнительные данные для callback
    """
    builder = InlineKeyboardBuilder()

    if page > 1:
        builder.add(InlineKeyboardButton(
            text="◀️ Назад",
            callback_data=f"{callback_prefix}_{page - 1}{extra_data}"
        ))

    builder.add(InlineKeyboardButton(
        text=f"{page}/{total_pages}",
        callback_data="no_action"
    ))

    if page < total_pages:
        builder.add(InlineKeyboardButton(
            text="Вперед ▶️",
            callback_data=f"{callback_prefix}_{page + 1}{extra_data}"
        ))

    builder.adjust(3)
    return builder.as_markup()