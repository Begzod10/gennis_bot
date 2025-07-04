import asyncio
import logging
from aiogram import Bot, Dispatcher, types, F
from app.handlers import router
from app.student.handlers import student_router
from app.teacher.handlers import teacher_router
from app.parent.handlers import parent_router
from app.db import engine, Base
from app import models
import os
from dotenv import load_dotenv
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis  # Redis for async

load_dotenv()

# Bot instance
bot = Bot(token=os.getenv('TOKEN'))

# Redis FSM Storage setup (DB 2)
redis_pool = redis.from_url(
    f"redis://{os.getenv('REDIS_HOST')}:{os.getenv('REDIS_PORT')}/{os.getenv('REDIS_DB_BOT')}"
)
storage = RedisStorage(redis=redis_pool)

# Dispatcher with Redis FSM
dp = Dispatcher(storage=storage)

api = os.getenv('API')


async def main():
    dp.include_router(router)
    dp.include_router(student_router)
    dp.include_router(teacher_router)
    dp.include_router(parent_router)
    # await init_models()
    await dp.start_polling(bot)


async def init_models():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print('Bot stopped')
