from aiogram import Router, F, types
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.utils.keyboard import InlineKeyboardBuilder

test = Router()


class TestStates(StatesGroup):
    waiting_for_answer = State()


# ✅ Test savollari ro‘yxati
html_savoli = [
    {
        "q": "HTML5’da <section> va <div> teglari orasidagi farq nimada?",
        "options": [
            "Ikkalasi ham bir xil ishlaydi",
            "<section> semantik teg, <div> esa semantik emas",
            "<div> faqat matn uchun ishlatiladi"
        ],
        "answer": "<section> semantik teg, <div> esa semantik emas"
    },
    {
        "q": "<canvas> tegi nima uchun ishlatiladi?",
        "options": [
            "Video joylash uchun",
            "Matn formatlash uchun",
            "Rasm va grafik chizish uchun"
        ],
        "answer": "Rasm va grafik chizish uchun"
    },
]


# 🔹 Testni boshlash tugmasi
def test_start_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Testni boshlash")],
        ],
        resize_keyboard=True
    )


# 🔹 Testlar ro‘yxatini chiqaruvchi funksiya (chaqiriladi ham, dekorator bilan ham ishlaydi)
async def start_test_handler_func(message: types.Message):
    tests = [
        {"id": 1, "name": "HTML"},
        {"id": 2, "name": "CSS"},
        {"id": 3, "name": "JavaScript"},
        {"id": 4, "name": "Python"},
        {"id": 5, "name": "Ingliz tili"},
        {"id": 6, "name": "Kimyo"},
    ]

    builder = InlineKeyboardBuilder()
    for test in tests:
        builder.button(
            text=test["name"],
            callback_data=f"select_test_{test['id']}"
        )
    builder.adjust(2)

    await message.answer(
        "🧠 Quyidagi testlardan birini tanlang:",
        reply_markup=builder.as_markup()
    )


# 🔹 Ushbu funksiya “📝 Testni boshlash” bosilganda avtomatik ishlaydi
@test.message(F.text == "📝 Testni boshlash")
async def start_test_handler(message: types.Message):
    await start_test_handler_func(message)


# 🔹 Test tanlanganda
@test.callback_query(F.data.startswith("select_test_"))
async def handle_selected_test(callback: types.CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split("_")[-1])

    tests = {
        1: "HTML",
        2: "CSS",
        3: "JavaScript",
        4: "Python",
        5: "Ingliz tili",
        6: "Kimyo"
    }

    test_name = tests.get(test_id, "Noma’lum test")

    # Hozircha HTML testini ishlatamiz
    if test_id == 1:
        question = html_savoli[0]["q"]
        options = html_savoli[0]["options"]

        builder = InlineKeyboardBuilder()
        for opt in options:
            builder.button(text=opt, callback_data=f"answer_{opt}")

        await callback.message.answer(
            f"✅ Siz <b>{test_name}</b> testini tanladingiz!\n\n"
            f"❓ <b>{question}</b>",
            parse_mode="HTML",
            reply_markup=builder.as_markup()
        )

        await state.set_state(TestStates.waiting_for_answer)
        await callback.answer()
    else:
        await callback.message.answer(f"❌ {test_name} testi hali tayyor emas.")
        await callback.answer()


# 🔹 Foydalanuvchi javobni yuborganda
@test.callback_query(F.data.startswith("answer_"))
async def check_answer(callback: types.CallbackQuery, state: FSMContext):
    user_answer = callback.data.replace("answer_", "").strip()
    correct_answer = html_savoli[0]["answer"]

    if user_answer == correct_answer:
        await callback.message.answer("✅ To‘g‘ri javob!", reply_markup=test_start_keyboard())
    else:
        await callback.message.answer("❌ Noto‘g‘ri javob!", reply_markup=test_start_keyboard())

    await state.clear()
    await callback.answer()
