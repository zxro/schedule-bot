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
    """
    escape_chars = r"_*[]()~`>#+-=|{}.!\\"
    for ch in escape_chars:
        text = text.replace(ch, f"\\{ch}")
    return text


@router.callback_query(F.data=="exit_admin_panel", IsAdminFilter())
async def exit_admin_panel(callback: CallbackQuery):
    await callback.message.delete()
    await callback.answer()


@router.message(F.text == "Админ панель", IsAdminFilter())
async def admin_panel_message(message: Message, state: FSMContext):
    await message.answer(text="Админ панель:", reply_markup=get_admin_kb())
    await state.clear()


@router.callback_query(F.data=="admin_panel", IsAdminFilter())
async def admin_panel_callback(callback: CallbackQuery, state: FSMContext):
    await callback.message.edit_text(text="Админ панель:", reply_markup=get_admin_kb())
    await callback.answer()
    await state.clear()


@router.callback_query(F.data == "add_admin", IsAdminFilter())
async def add_admin(callback: CallbackQuery, state: FSMContext):
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