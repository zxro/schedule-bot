from aiogram import BaseMiddleware
from typing import Callable, Dict, Any, Awaitable
from app.filters.ContextFilter import current_user_id, current_username


class UserContextMiddleware(BaseMiddleware):
    """
    Сохраняет user_id и username в contextvars для автоматического логирования.
    """

    async def __call__(
        self,
        handler: Callable[[Any, Dict[str, Any]], Awaitable[Any]],
        event: Any,
        data: Dict[str, Any]
    ) -> Any:
        user = getattr(event, "from_user", None)
        if user:
            current_user_id.set(user.id)
            current_username.set(user.username or "N/A")
        else:
            current_user_id.set("N/A")
            current_username.set("N/A")

        return await handler(event, data)