import asyncio
import logging
import os
import datetime
import jwt

from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.storage.redis import RedisStorage
import redis.asyncio as redis

from app.handlers import router
from app.student.handlers import student_router
from app.teacher.handlers import teacher_router
from app.parent.handlers import parent_router
from app.user.handlers import user_router
# from app.student.tests import student_routers

load_dotenv()
TOKEN = os.getenv("TOKEN")
GENNIS_TOKEN = os.getenv("GENNIS_TOKEN")
SECRET_KEY = os.getenv("JWT_SECRET", "supersecretkey")
TOKEN_EXPIRE_HOURS = 1

logging.basicConfig(level=logging.INFO)


def create_token(user_id: int) -> str:
    payload = {
        "user_id": user_id,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=TOKEN_EXPIRE_HOURS)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")
    return token


def verify_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return payload["user_id"]
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


async def main():
    bot = Bot(token=TOKEN)

    redis_pool = redis.from_url(
        f"redis://{os.getenv('REDIS_HOST', 'localhost')}:{os.getenv('REDIS_PORT', '6379')}/{os.getenv('REDIS_DB_BOT', '2')}"
    )
    storage = RedisStorage(redis=redis_pool)
    dp = Dispatcher(storage=storage)

    dp.include_router(router)
    dp.include_router(user_router)
    dp.include_router(student_router)
    dp.include_router(teacher_router)
    dp.include_router(parent_router)
    # dp.include_router(student_routers)

    @dp.message(Command("login"))
    async def login(message: types.Message):
        user_id = message.from_user.id
        token = create_token(user_id)
        await message.answer(f"Sizning tokeningiz: {token}")

    @dp.message(Command("me"))
    async def me(message: types.Message):
        try:
            token = message.text.split(" ")[1]
        except IndexError:
            await message.answer("Iltimos token yuboring: /me <token>")
            return

        user_id = verify_token(token)
        if user_id:
            await message.answer(f"Sizning ID: {user_id}")
        else:
            await message.answer("Token noto‘g‘ri yoki muddati tugagan")

    logging.info("Bot starting...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        print("Bot stopped!")
