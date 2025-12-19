# handlers.py

import logging
import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from db import *
from keyboards import *
from states import *

# --- НАСТРОЙКИ ---
ADMIN_ID = 8382571809
CONTACT_URL = "https://t.me/SalesFlowManager"  # URL для связи с админом
logger = logging.getLogger(__name__)


# --- ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ---

async def show_main_menu(event: types.Message | types.CallbackQuery, state: FSMContext, text: str = None):
    """Показывает главное меню. Умеет работать как с Message, так и с CallbackQuery."""
    await state.clear()
    user_id = event.from_user.id
    is_admin = get_user_role(user_id) == 'admin'
    sessions = get_user_sessions(user_id)
    welcome_text = text or (
        "Добро пожаловать! 🎉\n\nВыберите сессию:" if sessions else "Добро пожаловать! 🎉\n\nУ вас пока нет сессий. Создайте новую!")

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(welcome_text, reply_markup=get_main_menu_inline(sessions, is_admin))
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await event.bot.send_message(event.from_user.id, welcome_text,
                                         reply_markup=get_main_menu_inline(sessions, is_admin))
    else:
        await event.answer(welcome_text, reply_markup=get_main_menu_inline(sessions, is_admin))


async def show_session_menu(event: types.Message | types.CallbackQuery, state: FSMContext, session_id: int):
    """
    Показывает меню сессии. Умеет работать как с Message, так и с CallbackQuery.
    """
    await state.update_data(current_session_id=session_id)
    details = get_session_details(session_id)
    if not details:
        text = "Ошибка: сессия не найдена."
        reply_markup = get_main_menu_inline([], get_user_role(event.from_user.id) == 'admin')
        if isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(text, reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
                await event.bot.send_message(event.from_user.id, text, reply_markup=reply_markup)
        else:
            await event.answer(text, reply_markup=reply_markup)
        return

    status_text = "" if details['is_active'] else "\n\n<b>Сессия закрыта. Редактирование невозможно.</b>"
    menu_text = (
        f"📊 <b>Меню сессии: {details['name']}</b>{status_text}\n\n"
        f"💰 Баланс: <b>{details['balance']:.2f} {details['currency']}</b>\n"
        f"💸 Затраты: <b>{details['total_expenses']:.2f} {details['currency']}</b>\n"
        f"🔢 Продаж: <b>{details['sales_count']}</b>\n"
        f"💵 Мне должны: <b>{details['owed_to_me']:.2f} {details['currency']}</b>\n"
        f"🪙 Я должен: <b>{details['i_owe']:.2f} {details['currency']}</b>"
    )

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(menu_text, reply_markup=get_session_menu_inline(details['is_active']))
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await event.bot.send_message(event.from_user.id, menu_text,
                                         reply_markup=get_session_menu_inline(details['is_active']))
    else:
        await event.answer(menu_text, reply_markup=get_session_menu_inline(details['is_active']))


# --- MIDDLEWARE ---
class AccessMiddleware:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def __call__(self, handler, event: types.Message | types.CallbackQuery, data: dict) -> any:
        user_id = event.from_user.id
        is_admin = get_user_role(user_id) == 'admin'

        if isinstance(event, types.Message) and event.text == '/start':
            return await handler(event, data)
        if isinstance(event, types.CallbackQuery) and event.data in ['nav_start', 'cancel_action', 'session_menu']:
            return await handler(event, data)

        if isinstance(event, types.CallbackQuery) and event.data.startswith('admin_') and not is_admin:
            await event.answer("Доступ запрещен.", show_alert=True)
            return

        if not is_admin and not check_user_access(user_id):
            no_access_text = (
                f"👋 Привет! Это бот-бухгалтер.\n\n"
                f"Ваш Telegram ID: <code>{user_id}</code>\n\n"
                f"Доступ к боту платный.\n\n"
                f"Для получения доступа, пожалуйста, свяжитесь с администратором."
            )
            reply_markup = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Связаться с администратором", url=CONTACT_URL)]
            ])

            if isinstance(event, types.Message):
                await event.answer(no_access_text, reply_markup=reply_markup)
            elif isinstance(event, types.CallbackQuery):
                await event.answer("У вас нет доступа.", show_alert=True)
                await self.bot.send_message(chat_id=user_id, text=no_access_text, reply_markup=reply_markup)
            return

        return await handler(event, data)


class FSMTimeoutMiddleware:
    TIMEOUT_SECONDS = 300  # 5 минут

    async def __call__(self, handler, event: types.Message | types.CallbackQuery, data: dict) -> any:
        state: FSMContext = data['state']
        current_state = await state.get_state()
        if current_state:
            state_data = await state.get_data()
            last_activity_ts = state_data.get('timestamp')
            if last_activity_ts and (datetime.now().timestamp() - last_activity_ts > self.TIMEOUT_SECONDS):
                await state.clear()
                text = "Сессия ввода данных истекла. Начните заново."
                reply_markup = get_main_menu_inline([], get_user_role(event.from_user.id) == 'admin')
                if isinstance(event, types.Message):
                    await event.answer(text, reply_markup=reply_markup)
                else:
                    try:
                        await event.message.edit_text(text, reply_markup=reply_markup)
                    except Exception as e:
                        logger.error(f"Ошибка при редактировании сообщения: {e}")
                        await event.bot.send_message(event.from_user.id, text, reply_markup=reply_markup)
                return
            await state.update_data(timestamp=datetime.now().timestamp())
        elif isinstance(event, types.Message):
            await state.update_data(timestamp=datetime.now().timestamp())

        return await handler(event, data)


# --- ГЛАВНЫЕ ОБРАБОТЧИКИ ---

async def handle_start_command(message: Message, state: FSMContext):
    ensure_user_exists(message.from_user.id)

    is_admin = get_user_role(message.from_user.id) == 'admin'
    if not is_admin and not check_user_access(message.from_user.id):
        no_access_text = (
            f"👋 Привет! Это бот-бухгалтер.\n\n"
            f"Ваш Telegram ID: <code>{message.from_user.id}</code>\n\n"
            f"Доступ к боту платный.\n\n"
            f"Для получения доступа, пожалуйста, свяжитесь с администратором."
        )
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Связаться с администратором", url=CONTACT_URL)]
        ])
        await message.answer(no_access_text, reply_markup=reply_markup)
        return

    await show_main_menu(message, state)


async def navigate(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split('_', 1)[1]
    await state.clear()

    if action == "start":
        await show_main_menu(callback, state)
    elif action == "admin_panel":
        try:
            await callback.message.edit_text("Выберите действие в Админ-Панели:", reply_markup=get_admin_panel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Выберите действие в Админ-Панели:",
                                            reply_markup=get_admin_panel_inline())
    elif action == "create_session":
        try:
            await callback.message.edit_text("Введите название для новой сессии (макс. 50 символов):",
                                             reply_markup=get_cancel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id,
                                            "Введите название для новой сессии (макс. 50 символов):",
                                            reply_markup=get_cancel_inline())
        await state.set_state(CreateSession.name)
        await state.update_data(timestamp=datetime.now().timestamp())
    elif action.startswith("session_"):
        session_id = int(action.split('_', 1)[1])
        await show_session_menu(callback, state, session_id)
    elif action == "cancel_search_transaction":
        await show_transactions_list(callback, state, 'sale')
    elif action == "cancel_search_debt":
        debt_type = (await state.get_data()).get('debt_type')
        await show_debts_list(callback, state, debt_type)
    elif action == "menu":  # Handles the "Back to menu" button from lists
        session_id = (await state.get_data()).get('current_session_id')
        if session_id:
            await show_session_menu(callback, state, session_id)
        else:
            await show_main_menu(callback, state)

    await callback.answer()


# --- ОБРАБОТЧИКИ СОЗДАНИЯ СЕССИИ ---

async def process_session_name(message: Message, state: FSMContext):
    session_name = message.text.strip()
    if len(session_name) > 50 or len(session_name) < 3:
        return await message.answer("Название должно быть от 3 до 50 символов. Попробуйте еще раз:",
                                    reply_markup=get_cancel_inline())
    await state.update_data(name=session_name)
    await message.answer("Выберите валюту:", reply_markup=get_currency_inline())
    await state.set_state(CreateSession.currency)


async def process_currency_choice(callback: CallbackQuery, state: FSMContext):
    currency_map = {"currency_USDT": "USDT", "currency_RUB": "Рубль ПМР"}
    currency_name = currency_map[callback.data]
    await state.update_data(currency=currency_name)
    try:
        await callback.message.edit_text(f"Валюта: <b>{currency_name}</b>.\n\nВведите бюджет на сессию:")
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        await callback.bot.send_message(callback.from_user.id,
                                        f"Валюта: <b>{currency_name}</b>.\n\nВведите бюджет на сессию:")
    await state.set_state(CreateSession.budget)
    await callback.answer()


async def process_budget(message: Message, state: FSMContext):
    try:
        budget = float(message.text.replace(',', '.'))
        if budget <= 0:
            raise ValueError
    except ValueError:
        return await message.answer("Введите корректное положительное число.", reply_markup=get_cancel_inline())

    data = await state.get_data()
    add_session(message.from_user.id, data['name'], budget, data['currency'])
    await show_main_menu(message, state, f"✅ Сессия <b>'{data['name']}'</b> создана!")


# --- ОБРАБОТЧИКИ ДЕЙСТВИЙ В СЕССИИ ---

async def session_action_handler(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split('_', 1)[1]
    if action == "add_sale":
        try:
            await callback.message.edit_text("Введите сумму продажи:", reply_markup=get_cancel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Введите сумму продажи:",
                                            reply_markup=get_cancel_inline())
        await state.set_state(AddSale.amount)
    elif action == "add_expense":
        try:
            await callback.message.edit_text("Введите сумму затраты:", reply_markup=get_cancel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Введите сумму затраты:",
                                            reply_markup=get_cancel_inline())
        await state.set_state(AddExpense.amount)
    elif action == "manage_debts":
        try:
            await callback.message.edit_text("Управление долгами:", reply_markup=get_debt_management_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Управление долгами:",
                                            reply_markup=get_debt_management_inline())
    elif action == "list_sales":
        await show_transactions_list(callback, state, 'sale')
    elif action == "list_expenses":
        await show_transactions_list(callback, state, 'expense')
    elif action == "report":
        await show_report(callback, state)
    elif action == "close_confirm":
        session_id = (await state.get_data()).get('current_session_id')
        try:
            await callback.message.edit_text("Вы уверены, что хотите завершить сессию? Это действие необратимо.",
                                             reply_markup=get_confirmation_inline('close_session', session_id))
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id,
                                            "Вы уверены, что хотите завершить сессию? Это действие необратимо.",
                                            reply_markup=get_confirmation_inline('close_session', session_id))
    elif action == "menu":
        session_id = (await state.get_data()).get('current_session_id')
        await show_session_menu(callback, state, session_id)
    await callback.answer()


async def handle_list_debts(callback: CallbackQuery, state: FSMContext):
    debt_type_map = {"list_debts_owed_to_me": "owed_to_me", "list_debts_i_owe": "i_owe"}
    if callback.data in debt_type_map:
        debt_type = debt_type_map[callback.data]
        await state.update_data(debt_type=debt_type)  # Сохраняем тип для кнопки "назад"
        await show_debts_list(callback, state, debt_type)
    await callback.answer()


async def debt_category_handler(callback: CallbackQuery, state: FSMContext):
    debt_type_map = {"debt_owed_to_me": "owed_to_me", "debt_i_owe": "i_owe"}
    if callback.data in debt_type_map:
        await state.update_data(debt_type=debt_type_map[callback.data])
        try:
            await callback.message.edit_text("Введите сумму долга:", reply_markup=get_cancel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Введите сумму долга:",
                                            reply_markup=get_cancel_inline())
        await state.set_state(AddDebt.amount)
    await callback.answer()


# --- FSM для транзакций и долгов ---

async def process_sale_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0: raise ValueError
    except ValueError:
        return await message.answer("Введите корректную сумму.", reply_markup=get_cancel_inline())
    await state.update_data(amount=amount)
    await message.answer("Введите сумму затрат на эту продажу (если нет, введите 0):", reply_markup=get_cancel_inline())
    await state.set_state(AddSale.expense)


async def process_sale_expense(message: Message, state: FSMContext):
    try:
        expense = float(message.text.replace(',', '.'))
        if expense < 0: raise ValueError
    except ValueError:
        return await message.answer("Введите корректную сумму (0 или больше).", reply_markup=get_cancel_inline())
    await state.update_data(expense=expense)
    await message.answer("Введите название продажи (например, 'Звезды Телеграм'):", reply_markup=get_cancel_inline())
    await state.set_state(AddSale.description)


async def process_sale_description(message: Message, state: FSMContext):
    data = await state.get_data()
    session_id = data.get('current_session_id')
    add_transaction(session_id, 'sale', data['amount'], data['expense'], message.text[:100])

    await state.update_data(current_session_id=session_id)
    details = get_session_details(session_id)
    if not details:
        text = "Ошибка: сессия не найдена."
        reply_markup = get_main_menu_inline([], get_user_role(message.from_user.id) == 'admin')
        await message.answer(text, reply_markup=reply_markup)
        return

    status_text = "" if details['is_active'] else "\n\n<b>Сессия закрыта. Редактирование невозможно.</b>"
    menu_text = (
        f"📊 <b>Меню сессии: {details['name']}</b>{status_text}\n\n"
        f"💰 Баланс: <b>{details['balance']:.2f} {details['currency']}</b>\n"
        f"💸 Затраты: <b>{details['total_expenses']:.2f} {details['currency']}</b>\n"
        f"🔢 Продаж: <b>{details['sales_count']}</b>\n"
        f"💵 Мне должны: <b>{details['owed_to_me']:.2f} {details['currency']}</b>\n"
        f"🪙 Я должен: <b>{details['i_owe']:.2f} {details['currency']}</b>"
    )

    await message.answer(menu_text, reply_markup=get_session_menu_inline(details['is_active']))


async def process_expense_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0: raise ValueError
    except ValueError:
        return await message.answer("Введите корректную сумму.", reply_markup=get_cancel_inline())
    await state.update_data(amount=amount)
    await message.answer("На что была затрата (например, 'Реклама'):", reply_markup=get_cancel_inline())
    await state.set_state(AddExpense.description)


async def process_expense_description(message: Message, state: FSMContext):
    data = await state.get_data()
    session_id = data.get('current_session_id')
    add_transaction(session_id, 'expense', data['amount'], 0, message.text[:100])

    await state.update_data(current_session_id=session_id)
    details = get_session_details(session_id)
    if not details:
        text = "Ошибка: сессия не найдена."
        reply_markup = get_main_menu_inline([], get_user_role(message.from_user.id) == 'admin')
        await message.answer(text, reply_markup=reply_markup)
        return

    status_text = "" if details['is_active'] else "\n\n<b>Сессия закрыта. Редактирование невозможно.</b>"
    menu_text = (
        f"📊 <b>Меню сессии: {details['name']}</b>{status_text}\n\n"
        f"💰 Баланс: <b>{details['balance']:.2f} {details['currency']}</b>\n"
        f"💸 Затраты: <b>{details['total_expenses']:.2f} {details['currency']}</b>\n"
        f"🔢 Продаж: <b>{details['sales_count']}</b>\n"
        f"💵 Мне должны: <b>{details['owed_to_me']:.2f} {details['currency']}</b>\n"
        f"🪙 Я должен: <b>{details['i_owe']:.2f} {details['currency']}</b>"
    )

    await message.answer(menu_text, reply_markup=get_session_menu_inline(details['is_active']))


async def process_debt_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text.replace(',', '.'))
        if amount <= 0: raise ValueError
    except ValueError:
        return await message.answer("Введите корректную сумму.", reply_markup=get_cancel_inline())
    await state.update_data(amount=amount)
    await message.answer("Введите имя человека или организации:", reply_markup=get_cancel_inline())
    await state.set_state(AddDebt.person_name)


async def process_debt_person_name(message: Message, state: FSMContext):
    await state.update_data(person_name=message.text[:50])
    await message.answer("Введите описание долга (необязательно) или /skip:", reply_markup=get_cancel_inline())
    await state.set_state(AddDebt.description)


async def process_debt_description(message: Message, state: FSMContext):
    data = await state.get_data()
    session_id = data.get('current_session_id')
    description = "" if message.text == "/skip" else message.text[:100]
    add_debt(session_id, data['debt_type'], data['person_name'], data['amount'], description)

    await state.update_data(current_session_id=session_id)
    details = get_session_details(session_id)
    if not details:
        text = "Ошибка: сессия не найдена."
        reply_markup = get_main_menu_inline([], get_user_role(message.from_user.id) == 'admin')
        await message.answer(text, reply_markup=reply_markup)
        return

    status_text = "" if details['is_active'] else "\n\n<b>Сессия закрыта. Редактирование невозможно.</b>"
    menu_text = (
        f"📊 <b>Меню сессии: {details['name']}</b>{status_text}\n\n"
        f"💰 Баланс: <b>{details['balance']:.2f} {details['currency']}</b>\n"
        f"💸 Затраты: <b>{details['total_expenses']:.2f} {details['currency']}</b>\n"
        f"🔢 Продаж: <b>{details['sales_count']}</b>\n"
        f"💵 Мне должны: <b>{details['owed_to_me']:.2f} {details['currency']}</b>\n"
        f"🪙 Я должен: <b>{details['i_owe']:.2f} {details['currency']}</b>"
    )

    await message.answer(menu_text, reply_markup=get_session_menu_inline(details['is_active']))


# --- ОБРАБОТЧИКИ СПИСКОВ, ПОИСКА, РЕДАКТИРОВАНИЯ И УДАЛЕНИЯ ---

async def show_transactions_list(event: types.Message | types.CallbackQuery, state: FSMContext, t_type: str,
                                 search_query: str = None):
    session_id = (await state.get_data()).get('current_session_id')
    items = get_transactions_list(session_id, t_type, search_query)
    if not items:
        text = f"{'Продаж' if t_type == 'sale' else 'Затрат'} пока нет."
        if search_query: text = f"По запросу '{search_query}' ничего не найдено."
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Поиск", callback_data=f"search_{t_type}")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="session_menu")]
        ])
        if isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(text, reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
                await event.bot.send_message(event.from_user.id, text, reply_markup=reply_markup)
        else:
            await event.answer(text, reply_markup=reply_markup)
        return

    text = f"{'📈 Мои продажи' if t_type == 'sale' else '📉 Мои затраты'}:\n\n"
    for item in items:
        text += f"• {item['description'] or 'Без описания'} | +{item['amount']:.2f} / -{item['expense_amount']:.2f} | {item['date']}\n"

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text, reply_markup=get_items_list_inline(items, 'transaction', session_id,
                                                                                   search_query))
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await event.bot.send_message(event.from_user.id, text,
                                         reply_markup=get_items_list_inline(items, 'transaction', session_id,
                                                                            search_query))
    else:
        await event.answer(text, reply_markup=get_items_list_inline(items, 'transaction', session_id, search_query))


async def show_debts_list(event: types.Message | types.CallbackQuery, state: FSMContext, debt_type: str,
                          search_query: str = None):
    session_id = (await state.get_data()).get('current_session_id')
    items = get_debts_list(session_id, debt_type, search_query)
    if not items:
        text = f"{'Долгов вам' if debt_type == 'owed_to_me' else 'Ваших долгов'} пока нет."
        if search_query: text = f"По запросу '{search_query}' ничего не найдено."
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Поиск", callback_data=f"search_debt")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="session_menu")]
        ])
        if isinstance(event, CallbackQuery):
            try:
                await event.message.edit_text(text, reply_markup=reply_markup)
            except Exception as e:
                logger.error(f"Ошибка при редактировании сообщения: {e}")
                await event.bot.send_message(event.from_user.id, text, reply_markup=reply_markup)
        else:
            await event.answer(text, reply_markup=reply_markup)
        return

    text = f"{'💵 Мне должны' if debt_type == 'owed_to_me' else '🪙 Я должен'}:\n\n"
    for item in items:
        text += f"• {item['person_name']} - {item['amount']:.2f} | {item['date']}\n"

    if isinstance(event, CallbackQuery):
        try:
            await event.message.edit_text(text,
                                          reply_markup=get_items_list_inline(items, 'debt', session_id, search_query))
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await event.bot.send_message(event.from_user.id, text,
                                         reply_markup=get_items_list_inline(items, 'debt', session_id, search_query))
    else:
        await event.answer(text, reply_markup=get_items_list_inline(items, 'debt', session_id, search_query))


async def handle_search(callback: CallbackQuery, state: FSMContext):
    item_type = callback.data.split('_', 1)[1]
    await state.update_data(search_type=item_type)
    try:
        await callback.message.edit_text("Введите текст для поиска:", reply_markup=get_search_inline(item_type))
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        await callback.bot.send_message(callback.from_user.id, "Введите текст для поиска:",
                                        reply_markup=get_search_inline(item_type))
    await state.set_state(AddDebt.description)


async def process_search(message: Message, state: FSMContext):
    data = await state.get_data()
    search_type = data.get('search_type')
    search_query = message.text
    if not search_type: return

    if search_type == 'transaction':
        await show_transactions_list(message, state, 'sale', search_query)
    elif search_type == 'debt':
        debt_type = data.get('debt_type')
        await show_debts_list(message, state, debt_type, search_query)

    await state.clear()


# --- ИСПРАВЛЕННЫЕ ОБРАБОТЧИКИ РЕДАКТИРОВАНИЯ И УДАЛЕНИЯ ---

async def handle_edit_init(callback: CallbackQuery, state: FSMContext):
    # Фильтр гарантирует, что data имеет формат "edit_transaction_123" или "edit_debt_456"
    parts = callback.data.split('_')
    item_type = parts[1]  # 'transaction' или 'debt'
    item_id = int(parts[2])

    await state.update_data(edit_item_id=item_id, edit_item_type=item_type)
    try:
        await callback.message.edit_text("Что вы хотите изменить?",
                                         reply_markup=get_edit_item_inline(item_type, item_id))
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        await callback.bot.send_message(callback.from_user.id, "Что вы хотите изменить?",
                                        reply_markup=get_edit_item_inline(item_type, item_id))
    await callback.answer()


async def handle_edit_field(callback: CallbackQuery, state: FSMContext):
    # Фильтр гарантирует, что data имеет формат "edit_field_transaction_123_amount"
    # ИСПРАВЛЕНО: Используем split('_', 4) для корректной обработки полей с '_', например 'expense_amount'
    parts = callback.data.split('_', 4)
    if len(parts) < 5:
        logger.error(f"Неверный формат callback_data в handle_edit_field: {callback.data}")
        await callback.answer("Произошла ошибка. Попробуйте снова.", show_alert=True)
        return

    item_type = parts[2]  # 'transaction' или 'debt'
    try:
        item_id = int(parts[3])
    except ValueError:
        logger.error(f"Неверный ID элемента в callback_data: {parts[3]}")
        await callback.answer("Произошла ошибка. Неверный ID.", show_alert=True)
        return

    field = parts[4]  # 'amount', 'expense_amount', 'description', и т.д.

    await state.update_data(edit_item_id=item_id, edit_item_type=item_type, edit_field=field)

    if item_type == 'transaction':
        await state.set_state(EditTransaction.field)
    elif item_type == 'debt':
        await state.set_state(EditDebt.field)

    prompt_map = {
        'amount': "Введите новую сумму:",
        'expense_amount': "Введите новую сумму затрат:",
        'description': "Введите новое описание:",
        'person_name': "Введите новое имя:"
    }
    try:
        await callback.message.edit_text(prompt_map.get(field, "Введите новое значение:"),
                                         reply_markup=get_cancel_inline())
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        await callback.bot.send_message(callback.from_user.id, prompt_map.get(field, "Введите новое значение:"),
                                        reply_markup=get_cancel_inline())
    await callback.answer()


async def process_edit_field(message: Message, state: FSMContext):
    data = await state.get_data()
    item_type, item_id, field = data['edit_item_type'], data['edit_item_id'], data['edit_field']
    new_value = message.text.strip()

    if field in ['amount', 'expense_amount']:
        try:
            new_value = float(new_value.replace(',', '.'))
            if new_value < 0: raise ValueError
        except ValueError:
            return await message.answer("Введите корректное неотрицательное число.", reply_markup=get_cancel_inline())

    if item_type == 'transaction':
        update_transaction(item_id, field, new_value)
    elif item_type == 'debt':
        update_debt(item_id, field, new_value)

    session_id = data.get('current_session_id')
    await show_session_menu(message, state, session_id)


async def handle_repay_debt(callback: CallbackQuery, state: FSMContext):
    # Фильтр гарантирует формат "repay_debt_123"
    debt_id = int(callback.data.split('_')[2])
    update_debt(debt_id, 'is_repaid', 1)
    await callback.answer("Долг отмечен как погашенный.", show_alert=True)
    session_id = (await state.get_data()).get('current_session_id')
    await show_session_menu(callback, state, session_id)


async def handle_delete_confirm(callback: CallbackQuery, state: FSMContext):
    # Фильтр гарантирует, что data имеет формат "del_transaction_123_confirm" или "del_debt_456_confirm"
    parts = callback.data.split('_')
    item_type = parts[1]  # 'transaction' или 'debt'
    item_id = int(parts[2])

    await state.update_data(delete_item_type=item_type, delete_item_id=item_id)
    try:
        await callback.message.edit_text("Вы уверены, что хотите удалить эту запись?",
                                         reply_markup=get_confirmation_inline(f'del_{item_type}', item_id))
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        await callback.bot.send_message(callback.from_user.id, "Вы уверены, что хотите удалить эту запись?",
                                        reply_markup=get_confirmation_inline(f'del_{item_type}', item_id))
    await callback.answer()


async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    parts = callback.data.split('_', 3)
    if len(parts) < 4:
        logger.error(f"Неверный формат callback_data в process_confirmation: {callback.data}")
        await callback.answer("Произошла ошибка. Попробуйте снова.", show_alert=True)
        return

    action = f"{parts[1]}_{parts[2]}"
    item_id = int(parts[3])

    # ИСПРАВЛЕНО: Исправлена проверка для удаления транзакций. Было 'del_trans', стало 'del_transaction'
    if action == 'del_transaction':
        delete_transaction(item_id)
        await callback.answer("Транзакция удалена.", show_alert=True)
    elif action == 'del_debt':
        delete_debt(item_id)
        await callback.answer("Долг удален.", show_alert=True)
    elif action == 'close_session':
        close_session(item_id)
        details = get_session_details(item_id)
        reply_markup = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data=f"nav_session_{item_id}")]]
        )
        try:
            await callback.message.edit_text(
                f"🏁 Сессия '{details['name']}' завершена.\nИтоговая прибыль: {details['balance']:.2f} {details['currency']}",
                reply_markup=reply_markup
            )
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(
                callback.from_user.id,
                f"🏁 Сессия '{details['name']}' завершена.\nИтоговая прибыль: {details['balance']:.2f} {details['currency']}",
                reply_markup=reply_markup
            )
        return

    session_id = (await state.get_data()).get('current_session_id')
    await show_session_menu(callback, state, session_id)


async def cancel_action(callback: CallbackQuery, state: FSMContext):
    await navigate(callback, state)


async def cancel_edit(callback: CallbackQuery, state: FSMContext):
    item_type = callback.data.split('_', 2)[2]
    if item_type == 'transaction':
        await show_transactions_list(callback, state, 'sale')
    elif item_type == 'debt':
        debt_type = (await state.get_data()).get('debt_type')
        await show_debts_list(callback, state, debt_type)
    await callback.answer()


async def show_report(callback: CallbackQuery, state: FSMContext):
    session_id = (await state.get_data()).get('current_session_id')
    details = get_session_details(session_id)
    report_text = (
        f"📊 <b>Отчет по сессии: {details['name']}</b>\n\n"
        f"💰 Общий доход: <b>{details['total_sales']:.2f} {details['currency']}</b>\n"
        f"💸 Общие затраты: <b>{details['total_expenses']:.2f} {details['currency']}</b>\n"
        f"💵 Мне должны: <b>{details['owed_to_me']:.2f} {details['currency']}</b>\n"
        f"🪙 Я должен: <b>{details['i_owe']:.2f} {details['currency']}</b>\n\n"
        f"🟢 Чистая прибыль (без учета долгов): <b>{details['balance']:.2f} {details['currency']}</b>"
    )
    reply_markup = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ В меню", callback_data=f"nav_session_{session_id}")]]
    )
    try:
        await callback.message.edit_text(report_text, reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Ошибка при редактировании сообщения: {e}")
        await callback.bot.send_message(callback.from_user.id, report_text, reply_markup=reply_markup)


# --- АДМИН-ПАНЕЛЬ ---

async def admin_panel_handler(callback: CallbackQuery, state: FSMContext):
    action = callback.data.split('_', 1)[1]
    if action == "access":
        try:
            await callback.message.edit_text("Управление доступом:", reply_markup=get_access_management_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Управление доступом:",
                                            reply_markup=get_access_management_inline())
    elif action == "admins":
        try:
            await callback.message.edit_text("Управление админами:", reply_markup=get_admin_management_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Управление админами:",
                                            reply_markup=get_admin_management_inline())
    elif action == "broadcast":
        try:
            await callback.message.edit_text("Выберите аудиторию для рассылки:",
                                             reply_markup=get_broadcast_audience_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Выберите аудиторию для рассылки:",
                                            reply_markup=get_broadcast_audience_inline())
    elif action == "open_user":
        try:
            await callback.message.edit_text(
                "Введите Telegram ID и количество дней через пробел.\nПример: <code>987654321 30</code>",
                reply_markup=get_cancel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id,
                                            "Введите Telegram ID и количество дней через пробел.\nПример: <code>987654321 30</code>",
                                            reply_markup=get_cancel_inline())
        await state.set_state(AdminManageAccess.open_user)
    elif action == "close_user":
        try:
            await callback.message.edit_text("Введите Telegram ID пользователя, которому нужно закрыть доступ.",
                                             reply_markup=get_cancel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id,
                                            "Введите Telegram ID пользователя, которому нужно закрыть доступ.",
                                            reply_markup=get_cancel_inline())
        await state.set_state(AdminManageAccess.close_user)
    elif action == "open_all":
        grant_access_to_all()
        try:
            await callback.message.edit_text("✅ Доступ для всех пользователей открыт.",
                                             reply_markup=get_access_management_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "✅ Доступ для всех пользователей открыт.",
                                            reply_markup=get_access_management_inline())
    elif action == "close_all":
        revoke_temporary_access()
        try:
            await callback.message.edit_text("✅ Доступ для неоплативших пользователей закрыт.",
                                             reply_markup=get_access_management_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "✅ Доступ для неоплативших пользователей закрыт.",
                                            reply_markup=get_access_management_inline())
    elif action == "add_admin":
        try:
            await callback.message.edit_text("Введите Telegram ID нового администратора.",
                                             reply_markup=get_cancel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Введите Telegram ID нового администратора.",
                                            reply_markup=get_cancel_inline())
        await state.set_state(AdminManageAdmins.add)
    elif action == "remove_admin":
        try:
            await callback.message.edit_text("Введите Telegram ID администратора для удаления.",
                                             reply_markup=get_cancel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Введите Telegram ID администратора для удаления.",
                                            reply_markup=get_cancel_inline())
        await state.set_state(AdminManageAdmins.remove)
    elif action.startswith("broadcast_"):
        audience = action.split('_', 1)[1]
        await state.update_data(audience=audience)
        try:
            await callback.message.edit_text("Введите текст для рассылки.", reply_markup=get_cancel_inline())
        except Exception as e:
            logger.error(f"Ошибка при редактировании сообщения: {e}")
            await callback.bot.send_message(callback.from_user.id, "Введите текст для рассылки.",
                                            reply_markup=get_cancel_inline())
        await state.set_state(AdminBroadcast.text)
    await callback.answer()


async def process_open_user_access(message: Message, state: FSMContext):
    try:
        parts = message.text.split()
        user_id, days = int(parts[0]), int(parts[1])
        update_user_access(user_id, True, days)
        await message.answer(f"✅ Пользователю {user_id} открыт доступ на {days} дней.")
    except (ValueError, IndexError):
        await message.answer("❌ Неверный формат. Используйте: <code>ID ДНИ</code>")
    await state.clear()
    await show_main_menu(message, state)


async def process_close_user_access(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        update_user_access(user_id, False)
        await message.answer(f"✅ Пользователю {user_id} закрыт доступ.")
    except ValueError:
        await message.answer("❌ Неверный формат. Введите только ID пользователя.")
    await state.clear()
    await show_main_menu(message, state)


async def process_add_admin(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        add_admin(user_id)
        await message.answer(f"✅ Пользователь {user_id} теперь администратор.")
    except ValueError:
        await message.answer("❌ Неверный формат. Введите только ID пользователя.")
    await state.clear()
    await show_main_menu(message, state)


async def process_remove_admin(message: Message, state: FSMContext):
    try:
        user_id = int(message.text)
        if user_id == ADMIN_ID:
            return await message.answer("❌ Нельзя удалить главного администратора.")
        remove_admin(user_id)
        await message.answer(f"✅ Пользователь {user_id} больше не администратор.")
    except ValueError:
        await message.answer("❌ Неверный формат. Введите только ID пользователя.")
    await state.clear()
    await show_main_menu(message, state)


async def process_broadcast(message: Message, state: FSMContext, bot: Bot):
    audience = (await state.get_data()).get('audience')
    users_to_send = []
    all_users = get_all_users()
    if audience == "all":
        users_to_send = [u['user_id'] for u in all_users]
    elif audience == "access":
        users_to_send = [u['user_id'] for u in all_users if check_user_access(u['user_id'])]
    elif audience == "no_access":
        users_to_send = [u['user_id'] for u in all_users if not check_user_access(u['user_id'])]

    success_count = 0
    for user_id in users_to_send:
        try:
            await bot.send_message(chat_id=user_id, text=message.text)
            success_count += 1
            await asyncio.sleep(0.05)
        except Exception as e:
            logger.warning(f"Не удалось отправить сообщение пользователю {user_id}: {e}")

    await message.answer(f"✅ Рассылка завершена.\nУспешно отправлено: {success_count} из {len(users_to_send)}.")
    await state.clear()
    await show_main_menu(message, state)


# --- РЕГИСТРАЦИЯ ОБРАБОТЧИКОВ (ИСПРАВЛЕНО) ---
def register_handlers(dp: Dispatcher):
    """Регистрирует все обработчики в диспетчере."""

    # Навигация и главные команды
    dp.message.register(handle_start_command, CommandStart())
    dp.callback_query.register(navigate, F.data.startswith("nav_"))
    dp.callback_query.register(cancel_action, F.data == "cancel_action")

    # Создание сессии
    dp.message.register(process_session_name, CreateSession.name)
    dp.callback_query.register(process_currency_choice, F.data.startswith("currency_"))
    dp.message.register(process_budget, CreateSession.budget)

    # Действия в сессии
    dp.callback_query.register(session_action_handler, F.data.startswith("session_"))
    dp.callback_query.register(debt_category_handler, F.data.startswith("debt_"))
    dp.callback_query.register(handle_list_debts, F.data.startswith("list_debts_"))

    # FSM для транзакций и долгов
    dp.message.register(process_sale_amount, AddSale.amount)
    dp.message.register(process_sale_expense, AddSale.expense)
    dp.message.register(process_sale_description, AddSale.description)
    dp.message.register(process_expense_amount, AddExpense.amount)
    dp.message.register(process_expense_description, AddExpense.description)
    dp.message.register(process_debt_amount, AddDebt.amount)
    dp.message.register(process_debt_person_name, AddDebt.person_name)
    dp.message.register(process_debt_description, AddDebt.description)

    # Списки, поиск, редактирование, удаление
    dp.callback_query.register(handle_search, F.data.startswith("search_"))
    dp.message.register(process_search, F.text, AddDebt.description)

    # ИСПРАВЛЕНО: Более конкретные фильтры для избежания конфликтов
    dp.callback_query.register(handle_edit_init,
                               F.data.startswith("edit_transaction_") | F.data.startswith("edit_debt_"))
    dp.callback_query.register(handle_edit_field, F.data.startswith("edit_field_"))
    dp.message.register(process_edit_field, EditTransaction.field)
    dp.message.register(process_edit_field, EditDebt.field)

    dp.callback_query.register(handle_repay_debt, F.data.startswith("repay_debt_"))
    dp.callback_query.register(handle_delete_confirm,
                               F.data.startswith("del_transaction_") | F.data.startswith("del_debt_"))
    dp.callback_query.register(process_confirmation, F.data.startswith("confirm_"))
    dp.callback_query.register(cancel_edit, F.data.startswith("cancel_edit_"))

    # Админ-панель
    dp.callback_query.register(admin_panel_handler, F.data.startswith("admin_"))
    dp.message.register(process_open_user_access, AdminManageAccess.open_user)
    dp.message.register(process_close_user_access, AdminManageAccess.close_user)
    dp.message.register(process_add_admin, AdminManageAdmins.add)
    dp.message.register(process_remove_admin, AdminManageAdmins.remove)
    dp.message.register(process_broadcast, AdminBroadcast.text)