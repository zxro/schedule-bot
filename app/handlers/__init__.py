from aiogram import Dispatcher
from .start import router as start_router
from .schedule import router as schedule_router

def register_handlers(dp: Dispatcher):
    dp.include_router(start_router)
    dp.include_router(schedule_router)