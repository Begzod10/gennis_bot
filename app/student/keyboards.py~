from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

student_basic_reply_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="👤 Mening hisobim"),
            KeyboardButton(text="🎯 Test natijalari"),
        ],
        [
            KeyboardButton(text="💳 To'lovlar ro'yxati"),
            KeyboardButton(text="📚 Darslar ro'yxati"),
        ],
        [
            KeyboardButton(text="📝 Davomatlar ro'yxati"),
            KeyboardButton(text="📊 Baholar"),
        ],
        [
            KeyboardButton(text="🚪 Chiqish"),
            KeyboardButton(text="📝 Testni boshlash"),
        ]
    ],
    resize_keyboard=True,
    input_field_placeholder="👆 Birini tanlang!"
)

student_basic_reply_keyboard_test_type = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="🏁 Onlayn test yechish")],
        [KeyboardButton(text="⬅️ Orqaga")]
    ],
    resize_keyboard=True
)


def create_months_inline_keyboard(data, selected_year=None):
    year = data['current_year'] if not selected_year else selected_year
    months_list = []
    months_data = data['months']
    if isinstance(months_data, dict):
        months_data = [months_data]

    for item in months_data:
        if int(item['year']) == int(year):
            months_list = item['months']
            break

    keyboard = []
    row = []
    for i, month in enumerate(months_list):
        row.append(InlineKeyboardButton(text=month, callback_data=f"month_{month}"))
        if (i + 1) % 4 == 0:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def create_years_reply_keyboard(data):
    years_list = data['years']
    keyboard = []
    row = []
    for i, year in enumerate(years_list):
        row.append(KeyboardButton(text=year))
        if (i + 1) % 2 == 0:
            keyboard.append(row)
            row = []

    row.append(KeyboardButton(text="⬅️ Orqaga"))
    if row:
        keyboard.append(row)

    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True, one_time_keyboard=True)
