from aiogram import Dispatcher
from app.handlers.start import router as start_router
from app.handlers.sync import router as sync_router
from app.handlers.student_schedule import router as schedule_router
from app.handlers.registration import router as registration_router
from app.handlers.my_schedule import router as my_schedule_router
from app.handlers.admin import router as admin_router
from app.handlers.other_functions import router as other_functions_router
from app.handlers.clear_users import router as clear_users_router
from app.handlers.professor_schedule import router as professor_schedule_router

def register_handlers(dp: Dispatcher):
    """Регистрирует роутеры с обработчиками сообщений и callback"""
    dp.include_router(start_router)
    dp.include_router(sync_router)
    dp.include_router(schedule_router)
    dp.include_router(registration_router)
    dp.include_router(my_schedule_router)
    dp.include_router(admin_router)
    dp.include_router(other_functions_router)
    dp.include_router(clear_users_router)
    dp.include_router(professor_schedule_router)