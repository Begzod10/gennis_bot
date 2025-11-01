
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
import asyncio
from app.db import async_session
from app.models import TestResult

test = Router()


TEST_VARIANTS = ["Kimyo", "Ingliz tili", "HTML/CSS", "JavaScript", "Python", "Biologiya"]

HTML_TEST = [
    {"q": "1️⃣ HTML5’da &lt;section&gt; va &lt;div&gt; teglari orasidagi farq nimada?",
     "options": ["Ikkalasi ham bir xil ishlaydi",
                 "&lt;section&gt; semantik teg, &lt;div&gt; esa semantik emas",
                 "&lt;div&gt; faqat matn uchun ishlatiladi",
                 "Ikkalasi ham table ichida ishlaydi"],
     "answer": 1},
    {"q": "2️⃣ &lt;canvas&gt; tegi nima uchun ishlatiladi?",
     "options": ["Video joylash uchun",
                 "Matn formatlash uchun",
                 "Rasm va grafik chizish uchun",
                 "Formani yuborish uchun"],
     "answer": 2},
    {"q": "3️⃣ HTML’da accessibility uchun qaysi atribut ishlatiladi?",
     "options": ["aria-label", "alt-text", "screen-reader", "access-attr"],
     "answer": 0},
    {"q": "4️⃣ &lt;meta charset='UTF-8'&gt; tegi nima qiladi?",
     "options": ["Brauzerga sahifa kengligini belgilaydi",
                 "Tegishli script faylini ulaydi",
                 "Veb sahifa kodlash turini belgilaydi",
                 "Sahifa yuklanish vaqtini belgilaydi"],
     "answer": 2},
    {"q": "5️⃣ &lt;picture&gt; tegi nimaga xizmat qiladi?",
     "options": ["Turli ekran o‘lchamlariga mos rasm tanlash uchun",
                 "Rasmlarni guruhlash uchun",
                 "Rasm ustiga matn yozish uchun",
                 "Videoni o‘rnatish uchun"],
     "answer": 0},
]


active_questions = {}

TEST_VARIANTS = ["Kimyo", "Ingliz tili", "HTML/CSS", "JavaScript", "Python", "Biologiya"]

# =================== START ====================
@test.message(F.text == "📝 Testni boshlash")
async def start_test_handler(message: types.Message, state: FSMContext):
    builder = InlineKeyboardBuilder()
    for variant in TEST_VARIANTS:
        builder.button(text=variant, callback_data=f"variant_{variant}")
    builder.adjust(2)
    await message.answer("🧠 Qaysi testni tanlaysiz?", reply_markup=builder.as_markup())
    await state.clear()

# =================== VARIANT TANLASH ====================
@test.callback_query(F.data.startswith("variant_"))
async def choose_variant(callback: types.CallbackQuery, state: FSMContext):
    variant = callback.data.split("_")[1]
    await callback.message.answer(f"📝 {variant} testi boshlanmoqda!")

    if variant != "HTML/CSS":
        await callback.message.answer(f"{variant} testi hozircha tayyor emas.")
        await callback.answer()
        return

    await state.update_data(index=0, correct=0, answers={}, test_type=variant, user_id=callback.from_user.id)
    await callback.answer()
    await send_question(callback.message, state)

# =================== SAVOL CHIQARISH ====================
async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("index", 0)
    correct = data.get("correct", 0)
    answers = data.get("answers", {})
    test_type = data.get("test_type", "HTML/CSS")
    user_id = data.get("user_id")
    questions = HTML_TEST

    if index >= len(questions):
        total = len(questions)
        percent = (correct / total) * 100
        await message.answer(f"🎉 Test tugadi!\n\n🏁 Sizning natijangiz: {correct}/{total} ({percent:.1f}%)")

        # DB ga saqlash
        async with async_session() as session:
            result = TestResult(
                user_id=user_id,
                student_id=None,
                test_type=test_type,
                total_questions=total,
                correct_answers=correct,
                percent=percent,
                answers=answers
            )
            session.add(result)
            await session.commit()

        await state.clear()
        return

    q = questions[index]
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(q["options"]):
        builder.button(text=option, callback_data=f"answer_{index}_{i}")
    builder.adjust(1)

    msg = await message.answer(
        f"🧩 <b>{q['q']}</b>\n⏳ <b>10 soniya qoldi</b>",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

    async def countdown():
        for sec in range(9, 0, -1):
            try:
                await asyncio.sleep(1)
                await msg.edit_text(
                    f"🧩 <b>{q['q']}</b>\n⏳ <b>{sec} soniya qoldi</b>",
                    parse_mode="HTML",
                    reply_markup=builder.as_markup()
                )
            except Exception:
                return
        # Timeout tugadi, avtomatik keyingi savol
        data = await state.get_data()
        if data.get("index", 0) == index:
            await state.update_data(index=index + 1)
            await send_question(message, state)

    task = asyncio.create_task(countdown())
    active_questions[msg.message_id] = task

# =================== JAVOB QABUL QILISH ====================
@test.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    task = active_questions.pop(callback.message.message_id, None)
    if task:
        task.cancel()

    parts = callback.data.split("_")
    q_index = int(parts[1])
    user_answer = int(parts[2])
    data = await state.get_data()
    correct = data.get("correct", 0)
    answers = data.get("answers", {})
    test_type = data.get("test_type", "HTML/CSS")
    user_id = data.get("user_id")
    questions = HTML_TEST
    q = questions[q_index]
    correct_index = q["answer"]

    answers[str(q_index)] = user_answer
    await state.update_data(answers=answers)

    if user_answer == correct_index:
        correct += 1
        await callback.message.answer("✅ <b>To‘g‘ri javob!</b>", parse_mode="HTML")
    else:
        await callback.message.answer(
            f"❌ <b>Noto‘g‘ri.</b>\nTo‘g‘ri javob: <b>{q['options'][correct_index]}</b>",
            parse_mode="HTML"
        )

    total = len(questions)
    percent = (correct / total) * 100
    await callback.message.answer(f"📊 Sizning natijangiz: {correct}/{total} ({percent:.1f}%)")

    await state.update_data(correct=correct, index=q_index + 1)
    await callback.answer()
    await send_question(callback.message, state)
