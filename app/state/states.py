from aiogram.fsm.state import StatesGroup, State

class SyncStates(StatesGroup):
    confirm_full_sync = State()
    sync_faculty = State()
    sync_group_faculty = State()  # для выбора факультета при синхронизации группы
    sync_group_select = State()   # для выбора конкретной группы

class ShowSheduleStates(StatesGroup):
    choice_week = State()
    choice_group = State()
    choice_faculty = State()