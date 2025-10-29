from aiogram import Router, types
from aiogram.filters import CommandStart
from app.keyboards.main_menu_kb import get_main_menu_kb

router = Router()

@router.message(CommandStart())
async def cmd_start(message: types.Message):
    """
    @brief Обработчик команды /start.

    @details Отправляет приветственное сообщение и клавиатуру главного меню.

    @param message (types.Message): Объект сообщения Telegram.
    """

    kb = await get_main_menu_kb(message.from_user.id)
    await message.answer(
        text="Привет! 👋\n"
             "Я — бот расписания ТвГУ. Помогу тебе быстро находить нужное расписание 📚\n\n"
             "Вот что я умею:\n"
             "• Показывать расписание любой группы с любого факультет\n"
             "• Отображать расписание звонков\n"
             "• Показывать расписание преподавателей\n"
             "• Запоминать, где ты учишься, чтобы ты мог смотреть своё расписание в один клик\n\n",
        reply_markup=kb
    )