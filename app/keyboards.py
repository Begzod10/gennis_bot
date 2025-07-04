from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


login_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🔐 Tizimga kirish")]
    ],
    resize_keyboard=True,
    input_field_placeholder="👇 Davom etish uchun tugmani tanlang!"
)

