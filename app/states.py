from aiogram.fsm.state import State, StatesGroup


class MenuStates(StatesGroup):
    menu = State()
    attendances = State()
    salary = State()
    scores = State()


class LoginStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()




