import os
import asyncio
import requests
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.fsm.context import FSMContext

test = Router()

# --- Token va URL'lar ---
TOKEN = os.getenv("GENNIS_TOKEN", "YOUR_GENNIS_TOKEN_HERE")
TEST_LIST_URL = "https://classroom.gennis.uz/api/pisa/student/get/list"
TEST_QUESTIONS_URL = "https://classroom.gennis.uz/api/pisa/student/get"
TEST_FINISH_URL = "https://classroom.gennis.uz/api/pisa/student/finish"

headers = {
    "Authorization": f"Bearer {TOKEN}",
    "Accept": "application/json",
    "User-Agent": "MyScript/1.0"
}

active_questions = {}


# --- GET TEST LIST ---
def get_tests():
    try:
        response = requests.get(TEST_LIST_URL, headers=headers)
        if response.status_code != 200:
            print("❌ API status:", response.status_code, response.text)
            return []
        data = response.json()
        return [{"id": t["id"], "name": t["name"]} for t in data if "id" in t and "name" in t]
    except Exception as e:
        print("❌ Testlarni olishda xato:", e)
        return []


# --- GET QUESTIONS ---
def get_test_questions(test_id: int):
    try:
        url = f"{TEST_QUESTIONS_URL}/{test_id}"
        resp = requests.get(url, headers=headers)
        if resp.status_code != 200:
            print("❌ Savollarni olish xato:", resp.status_code, resp.text)
            return []
        data = resp.json()
        return data.get("questions", [])
    except Exception as e:
        print("❌ Savollarni olishda xato:", e)
        return []


# --- MARK TEST FINISHED ---
def mark_test_finished(test_id: int):
    try:
        url = f"{TEST_FINISH_URL}/{test_id}"
        r = requests.post(url, headers=headers)
        if r.status_code == 200:
            print(f"✅ Test {test_id} tugatildi")
            return True
        print(f"❌ Yakunlashda xato: {r.status_code} {r.text}")
        return False
    except Exception as e:
        print("❌ Testni yakunlash xato:", e)
        return False


# --- START TEST ---
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


# --- CHOOSE VARIANT ---
@test.callback_query(F.data.startswith("variant_"))
async def choose_variant(callback: types.CallbackQuery, state: FSMContext):
    test_id = int(callback.data.split("_")[1])
    questions = get_test_questions(test_id)
    if not questions:
        await callback.message.answer("❌ Bu testda savollar yo‘q!")
        await callback.answer()
        return

    await state.update_data(index=0, correct=0, test_id=test_id, questions=questions)
    await callback.message.answer("✅ Test boshlandi!")
    await callback.answer()
    await send_question(callback.message, state)


# --- SEND QUESTION ---
async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    index = data.get("index", 0)
    questions = data.get("questions", [])
    correct = data.get("correct", 0)

    if index >= len(questions):
        total = len(questions)
        percent = (correct / total) * 100
        await message.answer(f"🎉 Test tugadi!\n🏁 Natija: {correct}/{total} ({percent:.1f}%)")
        mark_test_finished(data["test_id"])
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
        f"🧩 <b>{text}</b>\n⏳ <b>10 soniya qoldi</b>",
        parse_mode="HTML",
        reply_markup=builder.as_markup()
    )

    async def countdown():
        for sec in range(9, 0, -1):
            try:
                await asyncio.sleep(1)
                await msg.edit_text(
                    f"🧩 <b>{text}</b>\n⏳ <b>{sec} soniya qoldi</b>",
                    parse_mode="HTML",
                    reply_markup=builder.as_markup()
                )
            except:
                return
        data = await state.get_data()
        if data.get("index", 0) == index:
            await state.update_data(index=index + 1)
            await send_question(message, state)

    task = asyncio.create_task(countdown())
    active_questions[msg.message_id] = task


# --- HANDLE ANSWER ---
@test.callback_query(F.data.startswith("answer_"))
async def handle_answer(callback: types.CallbackQuery, state: FSMContext):
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

    if user_answer == correct_index:
        correct += 1
        await callback.message.answer("✅ To‘g‘ri!")
    else:
        await callback.message.answer("❌ Noto‘g‘ri!")

    total = len(questions)
    percent = (correct / total) * 100
    await callback.message.answer(f"📊 Natija: {correct}/{total} ({percent:.1f}%)")

    await state.update_data(correct=correct, index=q_index + 1)
    await callback.answer()
    await send_question(callback.message, state)
