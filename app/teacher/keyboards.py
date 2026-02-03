import pprint
import json
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

teacher_basic_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👤 Mening hisobim"),
            KeyboardButton(text="💳 Oyliklar ro‘yhati")

        ],
        [
            KeyboardButton(text="📚 Darslar ro‘yhati"),
            KeyboardButton(text="🎯 Test natijalari")

        ],
        [
            KeyboardButton(text="👥 Guruhlar"),
            KeyboardButton(text="🚪 Chiqish")
        ],
    ],
    resize_keyboard=True,
    input_field_placeholder="👆 Birini tanlang!"
)


async def teacher_years_keyboard(data):
    years_list = data
    keyboard = ReplyKeyboardBuilder()
    for year in years_list:
        keyboard.button(text=year)
    keyboard.button(text="⬅️ Ortga qaytish")
    keyboard.adjust(2)
    return keyboard.as_markup(resize_keyboard=True)
