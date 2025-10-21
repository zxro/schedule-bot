import logging

from sqlalchemy import select

from app.bot import bot
from app.database.db import AsyncSessionLocal
from app.database.models import User, Group, Faculty

logger = logging.getLogger(__name__)

LIST_ADMINS = {}  # словарь: {id: "@username"}


async def create_first_admin(admin_id: int):
    """
    Функция создаёт первого админа и вставляет временные факультет и группу.
    """
    async with AsyncSessionLocal() as session:
        try:
            # Вставляем временный факультет
            faculty = Faculty(id=0, name="TEMP")
            session.add(faculty)

            # Вставляем временную группу
            group = Group(id=0, group_name="TEMP", faculty_id=0)
            session.add(group)

            # Вставляем пользователя-админа
            user = User(id=admin_id, group_id=0, faculty_id=0, role=1)
            session.add(user)

            await session.commit()

            logger.info(f"✅ Админ с ID {admin_id} добавлен.")

        except Exception as e:
            await session.rollback()
            logger.error(f"❌ Ошибка вставки временных данных: {e}")


async def remove_test_data():
    """
    Функция удаляет временный факультет и группу после проверки админов.
    """
    async with AsyncSessionLocal() as session:
        # Удаляем временную группу (id=0)
        test_group = await session.get(Group, 0)
        if test_group:
            await session.delete(test_group)

        # Удаляем временный факультет (id=0)
        test_faculty = await session.get(Faculty, 0)
        if test_faculty:
            await session.delete(test_faculty)

        await session.commit()
        logger.info("✅ Временные факультет и группа удалены.")


async def check_admins_start():
    """
    Проверяет наличие админов, если их нет - создаёт первого админа через ввод ID.
    """
    if len(LIST_ADMINS) != 0:
        return

    print("⚠️ Администраторов не существует, введите ID для первого админа: ")
    while True:
        try:
            admin_id = int(input())
            break
        except ValueError:
            print("⚠️ Неверный формат ID. Введите числовой ID: ")

    await create_first_admin(admin_id)
    await refresh_admin_list()
    await remove_test_data()


async def get_username_from_tg(user_id: int):
    """
    Получает username пользователя из Telegram.
    Если невозможно получить - возвращает 'none'
    """
    try:
        user = await bot.get_chat(user_id)
        return f"@{user.username}" if user.username else None
    except Exception as e:
        logger.warning(f"⚠️ Не удалось получить username для пользователя {user_id}: {e}")
        return None


async def refresh_admin_list():
    """Заполняет список администраторов с username из Telegram"""
    global LIST_ADMINS
    try:
        async with AsyncSessionLocal() as session:
            q = await session.execute(select(User).where(User.role == 1))
            users = q.scalars().all()

            LIST_ADMINS = {}

            if len(users) == 0:
                logger.info("⚠️ В базе данных не были найдены админы")
                return

            for user in users:
                username = await get_username_from_tg(user.id)
                LIST_ADMINS[user.id] = username

            logger.info(f"✅ Список администраторов обновлен: {len(LIST_ADMINS)} админов")

    except Exception as e:
        logger.error(f"❌ Ошибка при заполнении списка администраторов: {e}")
        LIST_ADMINS = {}


async def add_admin_to_list(user_id: int):
    """
    Добавляет одного администратора в список
    """
    global LIST_ADMINS
    try:
        username = await get_username_from_tg(user_id)
        LIST_ADMINS[user_id] = username
        logger.info(f"✅ Администратор {user_id} ({username}) добавлен в список")
    except Exception as e:
        logger.error(f"❌ Ошибка при добавлении администратора {user_id} в список: {e}")


async def remove_admin_from_list(user_id: int):
    """
    Удаляет одного администратора из списка
    """
    global LIST_ADMINS
    try:
        if user_id in LIST_ADMINS:
            username = LIST_ADMINS[user_id]
            del LIST_ADMINS[user_id]
            logger.info(f"✅ Администратор {user_id} ({username}) удален из списка")
        else:
            logger.warning(f"⚠️ Администратор {user_id} не найден в списке для удаления")
    except Exception as e:
        logger.error(f"❌ Ошибка при удалении администратора {user_id} из списка: {e}")


def is_admin(user_id: int):
    """Проверяет, является ли пользователь администратором"""
    return user_id in LIST_ADMINS


def get_admin_username(user_id: int):
    """Возвращает username администратора или 'none'"""
    return LIST_ADMINS.get(user_id, None)