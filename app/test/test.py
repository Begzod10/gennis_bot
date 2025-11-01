from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext
import asyncio

test = Router()

# === TEST SAVOLLARI ===
HTML_TEST = [
    {
        "q": "1️⃣ HTML5’da <section> va <div> teglari orasidagi farq nimada?",
        "options": [
            "Ikkalasi ham bir xil ishlaydi",
            "<section> semantik teg, <div> esa semantik emas",
            "<div> faqat matn uchun ishlatiladi",
            "Ikkalasi ham table ichida ishlaydi",
        ],
        "answer": 1
    },
    {
        "q": "2️⃣ <canvas> tegi nima uchun ishlatiladi?",
        "options": [
            "Video joylash uchun",
            "Matn formatlash uchun",
            "Rasm va grafik chizish uchun",
            "Formani yuborish uchun"
        ],
        "answer": 2
    },
    {
        "q": "3️⃣ HTML’da accessibility uchun qaysi atribut ishlatiladi?",
        "options": ["aria-label", "alt-text", "screen-reader", "access-attr"],
        "answer": 0
    },
    {
        "q": "4️⃣ <meta charset='UTF-8'> tegi nima qiladi?",
        "options": [
            "Brauzerga sahifa kengligini belgilaydi",
            "Tegishli script faylini ulaydi",
            "Veb sahifa kodlash turini belgilaydi",
            "Sahifa yuklanish vaqtini belgilaydi"
        ],
        "answer": 2
    },
    {
        "q": "5️⃣ <picture> tegi nimaga xizmat qiladi?",
        "options": [
            "Turli ekran o‘lchamlariga mos rasm tanlash uchun",
            "Rasmlarni guruhlash uchun",
            "Rasm ustiga matn yozish uchun",
            "Videoni o‘rnatish uchun"
        ],
        "answer": 0
    },
]


# === TEST BOSHLASH HANDLER ===
@test.message(F.text == "📝 Testni boshlash")
async def start_test_handler(message: types.Message, state: FSMContext):
    msg = await message.answer("🧠 HTML testi boshlanmoqda...\n\n⏳ 5 soniyadan keyin birinchi savol chiqadi!")

    # Taymer animatsiyasi
    for i in range(5, 0, -1):
        await msg.edit_text(f"⏳ <b>{i} soniya qoldi...</b>", parse_mode="HTML")
        await asyncio.sleep(1)

    await state.update_data(index=0, correct=0)
    await send_question(message, state)


# === SAVOL CHIQARISH FUNKSIYASI ===
async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("index", 0)

    if index >= len(HTML_TEST):
        correct = data.get("correct", 0)
        await message.answer(
            f"🎉 Test tugadi!\n\n🏁 Sizning natijangiz: <b>{correct}/{len(HTML_TEST)}</b>",
            parse_mode="HTML"
        )
        await state.clear()
        return

    q = HTML_TEST[index]
    builder = InlineKeyboardBuilder()
    for i, option in enumerate(q["options"]):
        builder.button(text=option, callback_data=f"answer_{index}_{i}")
    builder.adjust(1)

    await message.answer(f"🧩 <b>{q['q']}</b>", parse_mode="HTML", reply_markup=builder.as_markup())


# === JAVOBNI QABUL QILISH HANDLER ===
@test.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    parts = callback.data.split("_")
    q_index = int(parts[1])
    user_answer = int(parts[2])

    q = HTML_TEST[q_index]
    correct_index = q["answer"]
    data = await state.get_data()
    correct_count = data.get("correct", 0)

    # ✅ To‘g‘ri javobni tekshirish
    if user_answer == correct_index:
        correct_count += 1
        await callback.message.answer("✅ <b>To‘g‘ri javob!</b>", parse_mode="HTML")
    else:
        await callback.message.answer(
            f"❌ <b>Noto‘g‘ri.</b>\nTo‘g‘ri javob: <b>{q['options'][correct_index]}</b>",
            parse_mode="HTML"
        )

    # ✅ Keyingi savolga o‘tish taymeri
    msg = await callback.message.answer("⏳ <b>Keyingi savol 5 soniyadan keyin chiqadi...</b>", parse_mode="HTML")
    await state.update_data(index=q_index + 1, correct=correct_count)

    for i in range(5, 0, -1):
        await msg.edit_text(f"⏳ <b>{i} soniya qoldi...</b>", parse_mode="HTML")
        await asyncio.sleep(1)

    await callback.answer()
    await send_question(callback.message, state)
