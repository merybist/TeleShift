from aiogram.fsm.state import StatesGroup, State

class ConnectForm(StatesGroup):
    hash = State()

class ScheduleForm(StatesGroup):
    command = State()
    time = State()
    type = State()
