import logging

from aiogram.filters import BaseFilter
from aiogram.types import Message, CallbackQuery
from sqlalchemy import select

from app.database.db import AsyncSessionLocal
from app.database.models import User
from app.utils.custom_logging.ContextFilter import current_user_id, current_username

logger = logging.getLogger(__name__)

class IsAdminFilter(BaseFilter):
    """
    Фильтр, который пропускает только пользователей с ролью администратора.
    (role == 1)
    """
    async def __call__(self, obj: Message | CallbackQuery) -> bool:
        user_id = obj.from_user.id
        username = obj.from_user.username or "N/A"

        current_user_id.set(user_id)
        current_username.set(username)

        async with AsyncSessionLocal() as session:
            q = await session.execute(select(User).where(User.id == user_id))
            user = q.scalars().first()

        result = bool(user and user.role == 1)
        if not result:
            logger.warning(f"⚠️ Пользователь не являющийся администратором вызывает админ панель.")

        return result