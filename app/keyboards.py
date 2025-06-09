from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

login_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔐 Tizimga kirish")]
    ],
    resize_keyboard=True,
    input_field_placeholder="👇 Davom etish uchun tugmani tanlang!"
)

main = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='You tube', callback_data='you_tube')],
    [InlineKeyboardButton(text='Google', callback_data='google')],
    [InlineKeyboardButton(text='Yandex', callback_data='yandex')]
])
settings = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text='You tube', url='https://www.youtube.com/')],
])

cars = ['BMW', 'Audi', 'Mercedes', 'Tesla', 'Lada', 'Opel', 'Vaz', 'Mazda', 'Honda', 'Toyota', 'Nissan', 'Kia', 'Lexus']


async def inline_cars():
    keyboard = InlineKeyboardBuilder()
    for car in cars:
        keyboard.add(InlineKeyboardButton(text=car, url=f'https://www.google.com/search?q={car}'))

    return keyboard.adjust(2).as_markup()
