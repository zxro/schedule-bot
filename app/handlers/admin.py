import asyncio
import logging
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import update, select

from app.database.models import User
from app.filters.is_admin import IsAdminFilter
from app.keyboards.admin_kb import get_admin_kb
from app.state.states import AddAdminStates
from app.database.db import AsyncSessionLocal
from app.utils.admins.admin_list import add_admin_to_list, remove_admin_from_list, get_admin_username

router = Router()
logger = logging.getLogger(__name__)


def escape_md_v2(text: str) -> str:
    """
    Экранирует специальные символы для Telegram MarkdownV2.

    Telegram MarkdownV2 требует экранирования некоторых символов, чтобы они
    не интерпретировались как разметка. Эта функция добавляет обратный слэш
    перед каждым спецсимволом из списка, чтобы текст отображался корректно.

    Args:
        text (str): Исходный текст.

    Returns:
        str: Экранированный текст, безопасный для использования с MarkdownV2.
    """

    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    for ch in escape_chars:
        text = text.replace(ch, f"\\{ch}")
    return text


@router.callback_query(F.data=="exit_admin_panel", IsAdminFilter())
async def exit_admin_panel(callback: CallbackQuery):
    """
    Закрывает окно административной панели.

    Действия:
        Удаляет сообщение с панелью администратора.

    Args:
        callback (CallbackQuery): Объект callback-запроса от Telegram.
    """

    await callback.message.delete()
    await callback.answer()


@router.message(F.text == "Админ панель", IsAdminFilter())
async def admin_panel_message(message: Message, state: FSMContext):
    """
    Обрабатывает текстовую команду "Админ панель".

    Действия:
    1. Очищает текущее состояние FSM (если оно было установлено ранее).
    2. Отправляет пользователю сообщение с интерфейсом панели администратора.

    Args:
        message (Message): Объект сообщения от пользователя.
        state (FSMContext): Контекст конечного автомата состояний FSM.
    """

    await message.answer(text="Админ панель:", reply_markup=get_admin_kb())
    await state.clear()


@router.callback_query(F.data=="admin_panel", IsAdminFilter())
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    """
    Обрабатывает переход к административной панели через inline-кнопку.

    Действия:
    1. Редактирует текущее сообщение, заменяя его на меню панели администратора.
    2. Очищает состояние FSM.
    3. Подтверждает получение callback-запроса.

    Args:
        callback (CallbackQuery): Объект callback-запроса.
        state (FSMContext): Контекст состояния FSM.
    """

    await callback.message.edit_text(text="Админ панель:", reply_markup=get_admin_kb())
    await callback.answer()
    await state.clear()


@router.callback_query(F.data == "add_admin", IsAdminFilter())
async def add_admin(callback: CallbackQuery, state: FSMContext):
    """
    Инициирует процесс добавления нового администратора.

    Действия:
    1. Отображает сообщение с инструкцией ввести ID пользователя.
    2. Добавляет кнопку "◀️ Назад" для возврата в админ-панель.
    3. Переводит FSM в состояние ожидания ID (`AddAdminStates.waiting_id`).
    4. Сохраняет ID сообщения, чтобы потом его можно было удалить.

    Args:
        callback (CallbackQuery): Объект callback-запроса.
        state (FSMContext): Контекст состояния FSM.
    """


    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_panel")]
        ])
    await callback.message.edit_text("Введите ID пользователя для назначения администратором.\n"
                                     "Для того чтобы узнать id можно воспользоваться @username_to_id_bot",
                                     reply_markup=kb)
    await state.set_state(AddAdminStates.waiting_id)
    await callback.answer()
    await state.update_data(message_id=callback.message.message_id)


@router.message(StateFilter(AddAdminStates.waiting_id), IsAdminFilter())
async def reading_id(message: Message, state: FSMContext):
    """
    Обрабатывает ввод ID пользователя для назначения администратором.

    Действия:
    1. Удаляет предыдущее сообщение, где бот просил ввести ID.
    2. Проверяет, что введено число (ID).
    3. Не разрешает назначить администратором самого себя.
    4. Проверяет наличие пользователя в БД.
    5. Если пользователь найден и не администратор — обновляет его роль на 1.
    6. Добавляет пользователя в список администраторов.
    7. Обрабатывает ошибки и очищает состояние FSM.

    Args:
        message (Message): Объект сообщения с введённым ID.
        state (FSMContext): Контекст состояния FSM.

    Raises:
        ValueError: Если введённое значение не является числом.
        Exception: Любые другие ошибки работы с БД или Telegram API.
    """

    try:
        data = await state.get_data()
        message_id_to_delete = data.get("message_id")
        if message_id_to_delete:
            try:
                await message.bot.delete_message(chat_id=message.chat.id, message_id=message_id_to_delete)
            except Exception as e:
                logger.warning(f"⚠️ Не удалось удалить сообщение отправленное add_admin: {e}")

        user_id = int(message.text)

        if user_id == message.from_user.id:
            await message.answer("❌ Вы не можете назначить администратором самого себя.")
            await state.clear()
            return

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                await message.answer(f"❌ Пользователь с ID {user_id} не найден.")
                logger.info(f"⚠️ Попытка назначить администратором несуществующего пользователя {user_id}.")
                await state.clear()
                return

            if user.role == 1:
                await message.answer(f"ℹ️ Пользователь {user_id} уже является администратором.")
                logger.info(f"ℹ️ Попытка назначить администратором пользователя {user_id}, который уже им является.")
                await state.clear()
                return

            await session.execute(
                update(User)
                .where(User.id == user_id)
                .values(role=1)
            )
            await session.commit()

            success_message = f"✅ Пользователь {user_id} назначен администратором."
            await message.answer(success_message)
            logger.info(success_message)

            await add_admin_to_list(user_id)

    except ValueError as e:
        await message.answer("❌ Неверный формат ID. Введите числовой ID.")
        logger.error(f"❌ Ошибка при преобразовании ID '{message.text}' в handler reading_id: {e}")

    except Exception as e:
        await message.answer("❌ Произошла ошибка при обработке ID.")
        logger.error(f"❌ Ошибка в reading_id для текста '{message.text}': {e}")

    finally:
        await state.clear()


@router.callback_query(F.data == "list_of_admins", IsAdminFilter())
async def list_admins(callback: CallbackQuery):
    """
    Отображает список всех администраторов системы.

    Действия:
    1. Получает всех пользователей с ролью администратора из базы данных.
    2. Формирует список в формате MarkdownV2 с нумерацией, ID, ссылками и username.
    3. Подсвечивает текущего администратора пометкой "⭐ Это вы".
    4. Добавляет кнопки для удаления других администраторов.
    5. Добавляет справку с ссылками, если tg:// ссылка не работает.

    Args:
        callback (CallbackQuery): Объект callback-запроса.
    """

    async with AsyncSessionLocal() as session:
        stmt = select(User).where(User.role == 1)
        result = await session.execute(stmt)
        admins = result.scalars().all()

        if not admins:
            await callback.message.edit_text(
                text="📋 Список администраторов пуст.",
                reply_markup=InlineKeyboardBuilder()
                .button(text="◀️ Назад", callback_data="admin_panel")
                .as_markup()
            )
            await callback.answer()
            return

        admin_list = "📋 *Список администраторов:*\n\n"

        for i, admin in enumerate(admins, 1):
            escaped_id = escape_md_v2(str(admin.id))

            username = get_admin_username(admin.id)
            username_text = f" — {escape_md_v2(username)}" if username is not None else ""

            current_user_marker = " ⭐ Это вы" if admin.id == callback.from_user.id else ""

            admin_list += (f"{i}\\. ID `{escaped_id}`{username_text}"
                           f"\n     {current_user_marker}\n")

        admin_list += (
            "\nПри не рабочей или отсутствующей ссылке воспользуйтесь:\n"
            "app\\: tg\\:\\/\\/user\\?id\\=ID\n"
            "web\\: https\\:\\/\\/web\\.telegram\\.org\\/k\\/\\#ID\n"
        )

        builder = InlineKeyboardBuilder()
        for admin in admins:
            if admin.id != callback.from_user.id:
                builder.button(
                    text=f"🗑️ Удалить {admin.id}",
                    callback_data=f"remove_admin_{admin.id}"
                )

        builder.button(text="◀️ Назад", callback_data="admin_panel")
        builder.adjust(1)

        await callback.message.edit_text(
            admin_list,
            parse_mode="MarkdownV2",
            reply_markup=builder.as_markup(),
            disable_web_page_preview=True
        )
        await callback.answer()


@router.callback_query(F.data.startswith("remove_admin_"), IsAdminFilter())
async def remove_admin_handler(callback: CallbackQuery):
    """
    Обрабатывает удаление администратора по нажатию кнопки "🗑️ Удалить".

    Действия:
    1. Извлекает ID администратора из callback.data.
    2. Проверяет, что администратор не удаляет сам себя.
    3. Устанавливает пользователю роль на роль пользователя в базе данных.
    4. Удаляет администратора из списка LIST_ADMINS.
    5. Логирует все действия и отправляет уведомление.

    Args:
        callback (CallbackQuery): Объект callback-запроса.

    Raises:
        ValueError: Если ID некорректный.
        IndexError: Если формат callback.data некорректен.
        Exception: Любые другие ошибки в процессе удаления.
    """

    try:
        admin_id = int(callback.data.split("_")[2])

        if admin_id == callback.from_user.id:
            await callback.answer(text="❌ Вы не можете снять права с самого себя", show_alert=True)
            return

        async with AsyncSessionLocal() as session:
            user = await session.get(User, admin_id)
            if not user:
                await callback.answer(text="❌ Пользователь не найден", show_alert=True)
                return

            await session.execute(
                update(User)
                .where(User.id == admin_id)
                .values(role=0)
            )
            await session.commit()

        txt = f"✅ ID: {admin_id} снят с должности администратора."
        logger.info(txt)
        await callback.message.edit_text(text=txt)
        await callback.answer()

        await remove_admin_from_list(admin_id)

        await asyncio.sleep(1)
        await callback.message.edit_text(text="Админ панель", reply_markup=get_admin_kb())

    except (ValueError, IndexError) as e:
        await callback.answer("❌ Ошибка при обработке запроса", show_alert=True)
        logger.error(f"❌ Ошибка в при снятии роли администратора: {e}")
    except Exception as e:
        await callback.answer("❌ Произошла ошибка", show_alert=True)
        logger.error(f"❌ Ошибка в при снятии роли администратора: {e}")