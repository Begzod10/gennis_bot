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
from aiogram.fsm.storage.memory import MemoryStorage

load_dotenv()

bot = Bot(token=os.getenv('TOKEN'))
dp = Dispatcher(storage=MemoryStorage())
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


# run this once on startup


if __name__ == "__main__":
    # logging.basicConfig(level=logging.INFO)
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print('Bot stopped')
        pass
    # asyncio.run(main())
