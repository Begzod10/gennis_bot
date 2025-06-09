from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from typing import Callable, Dict, Awaitable, Any


class TestMiddleware(BaseMiddleware):
    async def __call__(self,
                       handler: Callable[[TelegramObject, Dict[str, object]], Awaitable[Any]],
                       event: TelegramObject,
                       data: Dict[str, Any]) -> Any:
        # print('TestMiddleware')
        result = await handler(event, data)
        # print('TestMiddleware end')
        return result
