from datetime import datetime
from aiogram import Router, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State, default_state
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.utils.markdown import hlink
from loguru import logger
from database_scripts.db import counter_parser_catalog_query
from middleware.throttling import throttled
from scripts.wb_category_parser import parser

router = Router()


class Parser_Category_States(StatesGroup):
    """стейты для запуска парсера по категории"""
    price_range = State()
    low_price = State()
    top_price = State()
    input_category = State()
    repeat_enter_link_category = State()


@throttled(rate=2)
@router.message(StateFilter(default_state), F.text == 'Парсер 🗂 категорий')
@router.message(StateFilter(default_state), Command("cpars"))
async def parser_wb_by_category_states(message: Message, state: FSMContext):
    """запуск стейтов по парсера по категориям"""
    builder = InlineKeyboardBuilder()
    builder.add(InlineKeyboardButton(text="Да", callback_data="yes"))
    builder.add(InlineKeyboardButton(text="Нет", callback_data="no"))
    await message.answer("Выбрать ценовой диапазон? ⚖️", reply_markup=builder.as_markup())
    await state.set_state(Parser_Category_States.price_range)


@router.message(StateFilter(Parser_Category_States.price_range))
async def error_state_price_range(message: Message, state: FSMContext):
    """стейт при некорректном вводе данных"""
    await message.reply(text='⛔️ Вы вышли из парсер-режима')
    await state.clear()


@router.callback_query(StateFilter(Parser_Category_States.price_range))
async def charge_price_range_state(callback: CallbackQuery, state: FSMContext):
    """стейт выбора ценового диапазона или ввода категории"""
    if callback.data == 'yes':  # если да, ввод нижней границы и переход к стейту верхней границы
        await callback.message.delete()
        await callback.message.answer(text='Введите нижнюю границу цен:')
        await state.set_state(Parser_Category_States.low_price)
    else:  # если нет, то ввод ссылки и переход в стейт ввода категории
        await callback.message.delete()
        await callback.message.answer(text='Вставте свою ссылку на категорию без фильтров. Например:\n<pre><code>https://www.wildberries.ru/catalog/elektronika/smartfony-i-telefony/vse-smartfony</code></pre>',
                                      disable_web_page_preview=False)
        await state.set_state(Parser_Category_States.input_category)


@router.message(StateFilter(Parser_Category_States.low_price))
async def low_price_range_state(message: Message, state: FSMContext):
    """стейт проверки ввода нижнего порога цены, переход к верхнему порогу цены"""
    if message.text.isdigit():
        if int(message.text) > 0:
            await state.update_data(low_price=message.text)
            await message.answer(text='Введите верхнюю границу цен:')
            await state.set_state(Parser_Category_States.top_price)
        else:
            await state.update_data(low_price=message.text)
            await message.reply(text='Нижняя граница должна быть больше 0.\nВведите еще раз:')
    else:
        await message.reply("⛔️ Некорректный ввод. Надо вводить число! Вы вышли из парсер-режима")
        await state.clear()


@router.message(StateFilter(Parser_Category_States.top_price))
async def top_price_range_state(message: Message, state: FSMContext):
    """стейт проверки ввода верхнего порога цены, переход к вводу категории"""
    data = await state.get_data()
    if message.text.isdigit():
        if int(data.get('low_price')) < int(message.text):
            await state.update_data(top_price=message.text)
            await message.answer(text='Вставте свою ссылку на категорию без фильтров. Например:\n<pre><code>https://www.wildberries.ru/catalog/elektronika/smartfony-i-telefony/vse-smartfony</code></pre>',
                                 disable_web_page_preview=False)
            await state.set_state(Parser_Category_States.input_category)
        else:
            await message.reply(text=f'Ваша нижняя граница меньше верхней!\nВведите число, больше чем {data.get("low_price")}')
            await state.update_data(top_price=message.text)
    else:
        await message.reply("⛔️ Некорректный ввод. Надо вводить число! Вы вышли из парсер-режима")
        await state.clear()


@router.message(StateFilter(Parser_Category_States.input_category))
async def run_parser_by_category(message: Message, state: FSMContext):
    """стейт ввода категории и запуска парсера"""
    if 'https://www.wildberries.ru/catalog/' in message.text:
        query_from_user = message.text.split('https://www.wildberries.ru/catalog/')[-1]
        counter_parser_catalog_query(user_id=message.from_user.id, query=query_from_user)  # запись в бд запроса/счет-ка
        data = await state.get_data()
        await state.clear()
        start = datetime.now()
        low_price = data.get('low_price')
        top_price = data.get('top_price')
        await message.reply(text=f'⚙️ Парсер начал работу c ценовым диапазоном от {low_price} до {top_price}...')
        filename_path = await parser(url=message.text, low_price=int(low_price), top_price=int(top_price), discount=0)
        logger.info(f'User: {message.from_user.id}({message.from_user.full_name}) run category_parser with price range "{low_price}-{top_price}": {"/".join((message.text.split("/")[4:]))}')
        end = datetime.now()
        total = end - start
        try:
            await message.answer_document(document=FSInputFile(filename_path),
                                          caption=f"✅Работа завершена успешно. Затраченное время: "
                                                  f"{str(total.seconds)} сек.\n"
                                                  f"{hlink(title='Канал парсера',url='https://t.me/timur_parsing_blog')}"
                                                  f" | Админ: @object_13")
        except TypeError:
            await message.answer('⛔️ Не удалось собрать данные! Обратитесь к администратору: @object_13')
            logger.error(f'User: {message.from_user.id}({message.from_user.full_name}) category_parser with "{message.text}"')
        await state.clear()
    else:
        await message.reply(text='⛔️ Некорректный ввод ссылки! Ссылку надо вводить без фильтров, как в образце.')
        logger.error(f'User: {message.from_user.id}({message.from_user.full_name}) category_parser with "{message.text}"')
        builder = InlineKeyboardBuilder()
        builder.add(InlineKeyboardButton(text="Да", callback_data="yes"))
        builder.add(InlineKeyboardButton(text="Нет", callback_data="no"))
        await message.answer("Ввести ссылку еще раз?", reply_markup=builder.as_markup())
        await state.set_state(Parser_Category_States.repeat_enter_link_category)


@router.message(StateFilter(Parser_Category_States.repeat_enter_link_category))
async def error_state_input_category(message: Message, state: FSMContext):
    """стейт при некорректном вводе данных"""
    await message.reply(text='⛔️ Вы вышли из парсер-режима')
    await state.clear()


@router.callback_query(StateFilter(Parser_Category_States.repeat_enter_link_category))
async def repeat_enter_link_category_state(callback: CallbackQuery, state: FSMContext):
    """повтор ввода ссылки после ошибки ввода и решении юзера о повторном вводе"""
    if callback.data == 'yes':
        logger.warning(f'User: {callback.from_user.id}({callback.from_user.full_name}) repeat enter category')
        await callback.message.answer(text='Введите ссылку на категорию еще раз (без фильтров):')
        await state.set_state(Parser_Category_States.input_category)
        await callback.message.delete()
    else:
        await callback.message.answer(text='Вы вышли из парсер-режима')
        await callback.message.delete()
        await state.clear()
