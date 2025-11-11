import os
import asyncio
import httpx
import requests
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

test = Router()

GENNIS_TOKEN = os.getenv(
    "GENNIS_TOKEN",
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2Mjg1NTIwMywianRpIjoiN2QzZjUwZjktYTJiZi00ODA5LWI1ZGYtZTk3M2U2YjA2ZjBmIiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjhkMDI3NzJjNTE5MzExZjBhNTQ4MzFkODQyNzBhMjIwIiwibmJmIjoxNzYyODU1MjAzLCJjc3JmIjoiZWRhMDllOTYtMWNmOC00YmNjLTg2YTMtNjc0NTAzYjgzZmQ5IiwiZXhwIjoxNzYyOTQxNjAzfQ.lRm38r8eo-t8G42UZe4Ne67wYTF6aXhRFJSiY5RfvJc"
)

TEST_LIST_URL = "https://classroom.gennis.uz/api/pisa/test/crud/34"
active_questions = {}

HEADERS = lambda token: {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "User-Agent": "GennisBot/1.0"
}


def get_tests():
    """Testlarni olish"""
    try:
        response = requests.get(TEST_LIST_URL, headers=HEADERS(GENNIS_TOKEN))
        print("Status:", response.status_code)
        if response.status_code != 200:
            print("⚠️ Server ishlamayapti", response.status_code)
            return []
        data = response.json()
        if isinstance(data, dict):
            return [{
                "id": data.get("id", 34),
                "name": data.get("name", "Nomaʼlum test")
            }]
        if isinstance(data, list):
            return [{"id": item["id"], "name": item["name"]} for item in data if "id" in item and "name" in item]
        print("⚠️ Format noto‘g‘ri:", type(data))
    except Exception as e:
        print("⚠️ Test olishda xatolik:", e)
    return []


async def get_test_questions(test_id: int):
    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.get(TEST_LIST_URL, headers=HEADERS(GENNIS_TOKEN))
    if resp.status_code != 200:
        return []

    data = resp.json()
    questions = []
    for block in data.get("pisa_blocks_right", []):
        text = block.get("editorState") or block.get("file") or block.get("text") or "Savol matni mavjud emas"
        options = [ans.get("text") for ans in block.get("answers", [])] if block.get("answers") else []
        correct = next((i for i, ans in enumerate(block.get("answers", [])) if ans.get("correct")), -1)
        questions.append({
            "q": text,
            "options": options,
            "answer": correct
        })
    return questions


@test.message(F.text == "📝 Testni boshlash")
async def start_test_handler(message: types.Message, state: FSMContext):
    tests = get_tests()
    if not tests:
        return await message.answer("❌ Testlar topilmadi!")
    builder = InlineKeyboardBuilder()
    for t in tests:
        builder.button(text=t["name"], callback_data=f"variant_{t['id']}")
    builder.adjust(1)
    await message.answer("🧠 Qaysi testni tanlaysiz?", reply_markup=builder.as_markup())
    await state.clear()


@test.callback_query(F.data.startswith("variant_"))
async def choose_variant(callback: types.CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split("_")[1])
    questions = await get_test_questions(test_id)
    if not questions:
        await callback.message.answer("❌ Bu testda savollar yo‘q!")
        await callback.answer()
        return
    await state.update_data(index=0, correct=0, test_id=test_id, questions=questions)
    await callback.message.answer("✅ Test boshlandi!")
    await callback.answer()
    await send_question(callback.message, state)


async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("index", 0)
    questions = data.get("questions", [])
    correct = data.get("correct", 0)

    if index >= len(questions):
        total = len(questions)
        percent = (correct / total) * 100 if total else 0
        await message.answer(f"🎉 Test tugadi!\n🏁 Natija: {correct}/{total} ({percent:.1f}%)")
        await state.clear()
        return

    q = questions[index]
    text = q.get("q", "")
    options = q.get("options", [])
    builder = InlineKeyboardBuilder()
    for i, opt in enumerate(options):
        builder.button(text=opt, callback_data=f"answer_{index}_{i}")
    builder.adjust(1)

    msg = await message.answer(
        f"🧩 {index + 1}. {text}\n⏳ 10 soniya qoldi",
        reply_markup=builder.as_markup()
    )

    async def countdown():
        for sec in range(9, 0, -1):
            try:
                await asyncio.sleep(1)
                await msg.edit_text(
                    f"🧩 {index + 1}. {text}\n⏳ {sec} soniya qoldi",
                    reply_markup=builder.as_markup()
                )
            except:
                return

        data_now = await state.get_data()
        if data_now.get("index", 0) == index:
            await state.update_data(index=index + 1)
            await send_question(message, state)

    task = asyncio.create_task(countdown())
    active_questions[msg.message_id] = task


@test.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
    # Agar savol uchun countdown ishlayotgan bo'lsa, to'xtatamiz
    task = active_questions.pop(callback.message.message_id, None)
    if task:
        task.cancel()

    _, q_index, user_answer = callback.data.split("_")
    q_index = int(q_index)
    user_answer = int(user_answer)

    data = await state.get_data()
    questions = data.get("questions", [])
    correct = data.get("correct", 0)
    correct_index = questions[q_index].get("answer", -1)

    if correct_index >= 0 and user_answer == correct_index:
        correct += 1
        await callback.message.answer("✅ Togri!")
    else:
        correct_text = questions[q_index]["options"][correct_index] if correct_index >= 0 else "Nomaʼlum"
        await callback.message.answer(f"❌ Notogri! To‘g‘ri javob: {correct_text}")

    await state.update_data(correct=correct, index=q_index + 1)
    await callback.answer()
    await send_question(callback.message, state)


# Matn orqali javob tekshiradigan handler
@test.message()
async def handle_text_answer(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("index", 0)
    questions = data.get("questions", [])
    if index >= len(questions):
        return  # Test tugagan

    q = questions[index]
    correct_index = q.get("answer", -1)
    correct_option = q["options"][correct_index] if correct_index >= 0 else None

    user_text = message.text.strip()

    if correct_option and user_text.lower() == correct_option.lower():
        correct = data.get("correct", 0) + 1
        await message.answer("✅ Togri!")
    else:
        correct = data.get("correct", 0)
        if correct_option:
            await message.answer(f"❌ Notogri! To‘g‘ri javob: {correct_option}")

    await state.update_data(correct=correct, index=index + 1)
    await send_question(message, state)
