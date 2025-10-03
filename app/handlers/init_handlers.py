from aiogram import Dispatcher
from app.handlers.start import router as start_router
from app.handlers.schedule import router as schedule_router
from app.handlers.sync import router as sync_router

def register_handlers(dp: Dispatcher):
    """Регистрирует роутеры с обработчиками сообщений и callback"""
    dp.include_router(start_router)
    dp.include_router(schedule_router)
    dp.include_router(sync_router)