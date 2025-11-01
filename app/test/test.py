from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
import asyncio

test = Router()

# === TEST VARIANTLARI ===
TEST_VARIANTS = ["Kimyo", "Ingliz tili", "HTML/CSS", "JavaScript", "Python", "Biologiya"]

# === HTML/CSS TEST SAVOLLARI ===
HTML_TEST = [
    {"q": "1️⃣ HTML5’da <section> va <div> teglari orasidagi farq nimada?",
     "options": ["Ikkalasi ham bir xil ishlaydi",
                 "<section> semantik teg, <div> esa semantik emas",
                 "<div> faqat matn uchun ishlatiladi",
                 "Ikkalasi ham table ichida ishlaydi"],
     "answer": 1},
    {"q": "2️⃣ <canvas> tegi nima uchun ishlatiladi?",
     "options": ["Video joylash uchun",
                 "Matn formatlash uchun",
                 "Rasm va grafik chizish uchun",
                 "Formani yuborish uchun"],
     "answer": 2},
    {"q": "3️⃣ HTML’da accessibility uchun qaysi atribut ishlatiladi?",
     "options": ["aria-label", "alt-text", "screen-reader", "access-attr"],
     "answer": 0},
    {"q": "4️⃣ <meta charset='UTF-8'> tegi nima qiladi?",
     "options": ["Brauzerga sahifa kengligini belgilaydi",
                 "Tegishli script faylini ulaydi",
                 "Veb sahifa kodlash turini belgilaydi",
                 "Sahifa yuklanish vaqtini belgilaydi"],
     "answer": 2},
    {"q": "5️⃣ <picture> tegi nimaga xizmat qiladi?",
     "options": ["Turli ekran o‘lchamlariga mos rasm tanlash uchun",
                 "Rasmlarni guruhlash uchun",
                 "Rasm ustiga matn yozish uchun",
                 "Videoni o‘rnatish uchun"],
     "answer": 0},
]

# === FAOL SAVOLLARNI SAQLASH ===
active_questions = {}

# === TESTNI BOSHLASH TUGMASI HANDLER ===
@test.message(F.text == "📝 Testni boshlash")
async def start_test_handler(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    for variant in TEST_VARIANTS:
        builder.button(text=variant, callback_data=f"variant_{variant}")
    builder.adjust(2)  # 2 ustun

    await message.answer("🧠 Qaysi testni tanlaysiz?", reply_markup=builder.as_markup())
    await state.clear()

# === VARIANT TANLASH HANDLER ===
@test.callback_query(F.data.startswith("variant_"))
async def choose_variant(callback: types.CallbackQuery, state: FSMContext):
    variant = callback.data.split("_")[1]
    await callback.message.answer(f"📝 {variant} testi boshlanmoqda!")

    if variant != "HTML/CSS":
        await callback.message.answer(f"{variant} testi hozircha tayyor emas.")
        await callback.answer()
        return

    await state.update_data(index=0, correct=0, test_type=variant)
    await callback.answer()
    await send_question(callback.message, state)

# === SAVOL CHIQARISH FUNKSIYASI ===
async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("index", 0)
    test_type = data.get("test_type", "HTML/CSS")

    # Faqat HTML/CSS testini ishlatamiz
    questions = HTML_TEST

    if index >= len(questions):
        correct = data.get("correct", 0)
        await message.answer(
            f"🎉 Test tugadi!\n\n🏁 Sizning natijangiz: <b>{correct}/{len(questions)}</b>",
            parse_mode="HTML"
        )
        await state.clear()
        return

    q = questions[index]
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(q["options"]):
        builder.button(text=option, callback_data=f"answer_{index}_{i}")
    builder.adjust(1)

    msg = await message.answer(f"🧩 <b>{q['q']}</b>", parse_mode="HTML", reply_markup=builder.as_markup())

    # 10 soniya timeout vazifasi
    async def auto_next():
        await asyncio.sleep(10)
        data = await state.get_data()
        if data.get("index", 0) == index:  # foydalanuvchi javob bermagan bo‘lsa
            await state.update_data(index=index + 1)
            await send_question(message, state)

    task = asyncio.create_task(auto_next())
    active_questions[msg.message_id] = task

# === JAVOB QABUL QILISH HANDLER ===
@test.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    # Timeout taskini bekor qilish
    task = active_questions.pop(callback.message.message_id, None)
    if task:
        task.cancel()

    parts = callback.data.split("_")
    q_index = int(parts[1])
    user_answer = int(parts[2])

    data = await state.get_data()
    questions = HTML_TEST
    q = questions[q_index]
    correct_index = q["answer"]
    correct_count = data.get("correct", 0)

    if user_answer == correct_index:
        correct_count += 1
        await callback.message.answer("✅ <b>To‘g‘ri javob!</b>", parse_mode="HTML")
    else:
        await callback.message.answer(
            f"❌ <b>Noto‘g‘ri.</b>\nTo‘g‘ri javob: <b>{q['options'][correct_index]}</b>",
            parse_mode="HTML"
        )

    await state.update_data(correct=correct_count, index=q_index + 1)
    await callback.answer()
    await send_question(callback.message, state)
