import asyncio
import logging
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis

from app.handlers import router
from app.student.handlers import student_router
from app.teacher.handlers import teacher_router
from app.parent.handlers import parent_router
from app.user.handlers import user_router

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

TOKEN = os.environ["TOKEN"]
API = os.environ["API"]


async def main():
    session = AiohttpSession(proxy=os.getenv("HTTPS_PROXY"))
    bot = Bot(token=TOKEN, session=session)

    redis_pool = redis.from_url(
        f"redis://{os.getenv('REDIS_HOST', 'localhost')}"
        f":{os.getenv('REDIS_PORT', '6379')}"
        f"/{os.getenv('REDIS_DB_BOT', '2')}"
    )

    storage = RedisStorage(redis=redis_pool)
    dp = Dispatcher(storage=storage)

    dp.include_router(router)
    dp.include_router(user_router)
    dp.include_router(student_router)
    dp.include_router(teacher_router)
    dp.include_router(parent_router)

    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot stopped")