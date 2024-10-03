import asyncio

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from loguru import logger
from database_scripts.db import delete_table, create_table
from handlers import parser_by_category_handler, greeting, admins_handler, parser_by_search_handler, \
    parser_by_brand_handler
from dotenv import load_dotenv
import os
from notifiers.logging import NotificationHandler
from middleware.throttling import ThrottlingMiddleware


load_dotenv()
TOKEN = os.getenv("TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

"""
pip freeze >requirements.txt
"""


async def main():
    params = {'token': TOKEN, 'chat_id': CHAT_ID}
    tg_handler = NotificationHandler(provider='telegram', defaults=params)
    logger.add(tg_handler, level='INFO')
    logger.info('Бот запущен!')
    storage = MemoryStorage()
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher(storage=storage)
    dp.include_router(parser_by_category_handler.router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot, polling_timeout=60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info('Бота упал!')
