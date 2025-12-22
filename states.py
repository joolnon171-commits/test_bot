from aiogram.fsm.state import State, StatesGroup


class CreateSession(StatesGroup):
    name = State()
    currency = State()
    budget = State()


class AddSale(StatesGroup):
    amount = State()
    expense = State()
    description = State()


class AddExpense(StatesGroup):
    amount = State()
    description = State()


class AddDebt(StatesGroup):
    debt_type = State()
    person_name = State()
    amount = State()
    description = State()


class EditTransaction(StatesGroup):
    trans_id = State()
    field = State()  # 'amount', 'description', etc.


class EditDebt(StatesGroup):
    debt_id = State()
    field = State()


class AdminManageAccess(StatesGroup):
    open_user = State()
    close_user = State()


class AdminManageAdmins(StatesGroup):
    add = State()
    remove = State()


class AdminBroadcast(StatesGroup):
    text = State()