import logging

from sqlalchemy import select

from app.bot import bot
from app.database.db import AsyncSessionLocal
from app.database.models import User, Group, Faculty

logger = logging.getLogger(__name__)

LIST_ADMINS = {}  # словарь: {id: "@username"}


async def create_first_admin(admin_id: int):
    """
    Создаёт первого администратора и временные записи в БД.

    При отсутствии администраторов функция:
    1. Добавляет временный факультет с id=0 и именем 'TEMP'.
    2. Добавляет временную группу с id=0 и faculty_id=0.
    3. Создаёт пользователя с переданным ID и ролью администратора (role=1).
    4. Фиксирует изменения в базе данных.

    Временные записи впоследствии удаляются функцией `remove_test_data()`.

    Args:
        admin_id (int): Telegram ID первого администратора.

    Raises:
        Exception: При ошибках вставки или проблемах с транзакцией (фиксируется в логах).
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
    Удаляет временные записи факультета и группы после инициализации администратора.

    Эта функция вызывается после успешного создания первого администратора.
    Удаляются записи с `id = 0` из таблиц `faculties` и `groups`.

    Логирует факт удаления и пропускает отсутствие записей без ошибок.
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
    Проверяет наличие администраторов при запуске бота.

    Алгоритм:
    1. Если список администраторов (`LIST_ADMINS`) не пуст — выход.
    2. Если админов нет:
       - запрашивает ID первого администратора через консольный ввод;
       - создаёт временные записи (см. `create_first_admin`);
       - обновляет список администраторов в памяти (`refresh_admin_list`);
       - удаляет тестовые данные (`remove_test_data`).

    Используется при первом запуске бота или после очистки базы данных.

    Raises:
        ValueError: Если введён некорректный ID (ловится и повторяется ввод).
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
    Получает username пользователя из Telegram API.

    Использует метод `bot.get_chat(user_id)` для получения информации о пользователе.
    Возвращает username в формате `@username` или None, если username отсутствует
    или произошла ошибка (например, бот не имеет доступа к пользователю).

    Args:
        user_id (int): Telegram ID пользователя.

    Returns:
        str | None: Username пользователя в формате '@name', либо None.

    Raises:
        Exception: Все ошибки логируются и не прерывают выполнение программы.
    """

    try:
        user = await bot.get_chat(user_id)
        return f"@{user.username}" if user.username else None
    except Exception as e:
        logger.warning(f"⚠️ Не удалось получить username для пользователя {user_id}: {e}")
        return None


async def refresh_admin_list():
    """
    Обновляет глобальный список администраторов из базы данных.

    Действия:
    1. Загружает из таблицы `users` всех пользователей с администратора.
    2. Для каждого администратора получает username через `get_username_from_tg`.
    3. Заполняет глобальный словарь `LIST_ADMINS` формата `{user_id: "@username"}`.
    4. Логирует количество найденных администраторов.

    Если администраторов в базе нет — словарь остаётся пустым, но бот продолжает работу.

    Raises:
        Exception: Ошибки соединения с БД или Telegram API логируются.
    """

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
    Добавляет нового администратора в кэш `LIST_ADMINS`.

    Используется после успешного назначения роли администратора через бота.

    Args:
        user_id (int): Telegram ID пользователя, получившего права администратора.

    Логирует успешное добавление и username, если он найден.
    Ошибки Telegram API или записи в словарь не критичны и просто логируются.
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
    Удаляет администратора из локального списка `LIST_ADMINS`.

    Args:
        user_id (int): Telegram ID администратора для удаления.

    Поведение:
    - Если пользователь найден — удаляется из словаря.
    - Если нет — логируется предупреждение.
    - Все ошибки отлавливаются и логируются без прерывания выполнения.
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
    """
    Проверяет, является ли пользователь администратором.

    Args:
        user_id (int): Telegram ID пользователя.

    Returns:
        bool: True — если пользователь есть в `LIST_ADMINS`, иначе False.
    """

    return user_id in LIST_ADMINS


def get_admin_username(user_id: int):
    """
    Возвращает username администратора по его ID.

    Args:
        user_id (int): Telegram ID администратора.

    Returns:
        str | None: Username в формате '@name', если найден,
                    иначе None (если нет в списке или username отсутствует).
    """

    return LIST_ADMINS.get(user_id, None)