import logging

from app.keyboards.base_kb import refresh_base_keyboards
from app.keyboards.find_kb import refresh_find_keyboards
from app.keyboards.registration_kb import refresh_reg_keyboards
from app.keyboards.sync_kb import refresh_sync_keyboards

logger = logging.getLogger(__name__)

async def refresh_all_keyboards():
    await refresh_base_keyboards()

    await refresh_sync_keyboards()
    await refresh_find_keyboards()
    await refresh_reg_keyboards()

    logger.info('Все клавиатуры обновлены')