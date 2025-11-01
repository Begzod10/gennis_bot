from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
import asyncio

test = Router()


# --- HOLAT MASHINASI (FSM) ---
class TestStates(StatesGroup):
    waiting_for_answer = State()


# --- SAVOLLAR RO‘YXATI ---
HTML_SAVOLLAR = [
    {
        "q": "1️⃣ HTML5’da <section> va <div> teglari orasidagi farq nimada?",
        "a": "<section> semantik teg, <div> esa semantik emas"
    },
    {
        "q": "2️⃣ <canvas> tegi nima uchun ishlatiladi?",
        "a": "Rasm va grafik chizish uchun"
    },
    {
        "q": "3️⃣ HTML’da accessibility uchun qaysi atribut ishlatiladi?",
        "a": "aria-label"
    },
    {
        "q": "4️⃣ <meta charset='UTF-8'> tegi nima qiladi?",
        "a": "Veb sahifa kodlash turini belgilaydi"
    },
    {
        "q": "5️⃣ <picture> tegi nimaga xizmat qiladi?",
        "a": "Turli ekran o‘lchamlariga mos rasm tanlash uchun"
    },
]


# --- TESTNI BOSHLASH ---
@test.message(F.text == "📝 Testni boshlash")
async def start_test_handler(message: types.Message, state: FSMContext):
    await message.answer("🧠 HTML testi boshlanmoqda...\n5 soniyadan keyin birinchi savol chiqadi...")
    await asyncio.sleep(5)
    await state.update_data(current_index=0, correct=0)
    await send_question(message, state)


# --- SAVOL YUBORISH FUNKSIYASI ---
async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("current_index", 0)

    if index >= len(HTML_SAVOLLAR):
        correct = data.get("correct", 0)
        await message.answer(f"🎉 Test tugadi!\n✅ Sizning natijangiz: {correct}/{len(HTML_SAVOLLAR)}")
        await state.clear()
        return

    question = HTML_SAVOLLAR[index]["q"]
    await message.answer(question)
    await state.set_state(TestStates.waiting_for_answer)


# --- JAVOB TEKSHIRISH ---
@test.message(TestStates.waiting_for_answer)
async def check_answer(message: types.Message, state: FSMContext):
    user_answer = message.text.strip().lower()
    data = await state.get_data()
    index = data.get("current_index", 0)
    correct_count = data.get("correct", 0)

    correct_answer = HTML_SAVOLLAR[index]["a"].lower()

    if user_answer == correct_answer:
        correct_count += 1
        await message.answer("✅ To‘g‘ri javob!")
    else:
        await message.answer(f"❌ Noto‘g‘ri.\nTo‘g‘ri javob: {HTML_SAVOLLAR[index]['a']}")

    await state.update_data(current_index=index + 1, correct=correct_count)

    # 5 sekunddan keyin keyingi savol chiqadi
    await asyncio.sleep(5)
    await send_question(message, state)
