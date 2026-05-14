from aiogram.fsm.state import StatesGroup, State

class ConnectForm(StatesGroup):
    hash = State()
