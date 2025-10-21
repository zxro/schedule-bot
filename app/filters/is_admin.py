import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery

from app.utils.custom_logging.ContextFilter import current_user_id, current_username
from app.utils.admins.admin_list import is_admin

logger = logging.getLogger(__name__)


class IsAdminFilter(BaseFilter):
    """
    Фильтр, который пропускает только пользователей с ролью администратора.
    Использует кэшированный список LIST_ADMINS для быстрой проверки.
    """

    async def __call__(self, obj: Message | CallbackQuery) -> bool:
        user_id = obj.from_user.id
        username = obj.from_user.username or "N/A"

        current_user_id.set(user_id)
        current_username.set(username)

        result = is_admin(user_id)

        if not result:
            logger.warning(f"🚨 Попытка несанкционированного доступа к админ-функциям.")

        return result