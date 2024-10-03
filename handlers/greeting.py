from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command
from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.utils.markdown import hlink
from keyboards.menu import main_menu

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.answer(f"Добро пожаловать {message.from_user.full_name} на парсер Wilberries от @happypython_team",
                         reply_markup=main_menu)


@router.message(F.text == 'О парсере Wildberries 💬')
@router.message(Command("about"))
async def cmd_start(message: Message):
    await message.answer(text=f'Перед вами парсер Wildberries!\n\nНа данный момент доступно:\n'
                              f'- парсинг по категориям;\n'
                              f'- ...\n\n'
                              f'Результат эксель файл с данными о сборе: id, названия, цены, остатков и т.д.\n\n'
                              f'Функционал будет расширяться на основе вашей обратной связи, так что пишите\n\n'
                              f'Телеграм канал: {hlink(title="Тимур и его блог", url="https://t.me/timur_parsing_blog")}\n'
                              f'Чат обсуждения: {hlink(title="Парсинг/Фриланс", url="https://t.me/+zQRr-6KAKt02Nzky")}\n'
                              f'По Вопросам, предложениям или совместном проекте писать:\n{hlink(title="Галимов Тимур", url="https://t.me/object_13")}',
                         reply_markup=main_menu,
                         disable_web_page_preview=True)


@router.message()
async def bot_echo(message: Message):
    await message.reply(f"'{message.text}' - не могу понять, что вы хотели этим сказать\n"
                        f"Вы не выбрали команду. Я не знаю, что вы хотите", reply_markup=main_menu)
