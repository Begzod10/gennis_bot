import os
import asyncio
import json
import requests
from dotenv import load_dotenv
from aiogram import F, Router, types
from aiogram.types import Message
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# Local importlar
from .keyboards import (
    create_years_reply_keyboard,
    create_months_inline_keyboard,
    student_basic_reply_keyboard,
    student_basic_reply_keyboard_test_type
)
from .utils import get_student
from app.states import MenuStates

# Router
student_router = Router()

# .env dan o‘qish
load_dotenv()
API = os.getenv('API')
GENNIS_TOKEN = os.getenv("GENNIS_TOKEN")


# ----------------------------- #
#      🧠 TEST STATE CLASS      #
# ----------------------------- #
class TestStates(StatesGroup):
    question_number = State()
    score = State()
    questions = State()
    waiting_answer = State()
    test_id = State()
    timer_task = State()


# ----------------------------- #
#         🧩 HELPERS            #
# ----------------------------- #
def save_result(user_id, username, score, total, percent):
    """Natijani bazaga yoki logga yozish"""
    print(f"✅ Natija saqlandi: {user_id} | {username} | {score}/{total} ({percent}%)")


def get_tests():
    """Testlar ro‘yxatini olish"""
    url = "https://classroom.gennis.uz/api/pisa/test/crud/34"
    headers = {"Authorization": f"Bearer {GENNIS_TOKEN}"}
    try:
        res = requests.get(url, headers=headers)
        data = res.json()
        if isinstance(data, dict):
            return [{"id": data.get("id", 34), "name": data.get("name", "Noma’lum test")}]
        elif isinstance(data, list):
            return [{"id": t["id"], "name": t["name"]} for t in data if "id" in t and "name" in t]
    except Exception as e:
        print(f"❌ Test olishda xato: {e}")
    return []


# ----------------------------- #
#       💳 TO‘LOVLAR BLOKI      #
# ----------------------------- #
@student_router.message(F.text == "💳 To'lovlar ro‘yhati")
async def get_payments_list(message: Message):
    telegram_user = message.from_user
    student = get_student(telegram_user.id)
    response = requests.get(f'{API}/api/bot/students/payments/{student.platform_id}')
    payments = response.json().get('payments', [])
    if not payments:
        await message.answer("⚠️ To'lovlar topilmadi.")
        return

    text = f"📋 <b>{student.name}, so'nggi to'lovlar ro'yxati:</b>\n\n"
    text += "{:<15} {:<12} {:<10}\n".format("Sana", "Miqdor", "Turi")
    text += "-" * 40 + "\n"
    for pay in payments:
        text += "{:<5} {:<12} {:<10}\n".format(pay['date'], pay['amount'], pay['payment_type'])
    await message.answer(text, parse_mode="HTML")

# -----------TEST------------------ #
@student_router.message(F.text == "🎯 Test natijalari")
async def test_types(message: Message):
    await message.answer("👆 Iltimos, quyidagilardan birini tanlang:",
                         reply_markup=student_basic_reply_keyboard_test_type())


@student_router.message(F.text == "📄 Offlayn test natijalari")
async def offline_results(message: Message):
    telegram_id = message.from_user.id
    student = get_student(telegram_id)
    response = requests.get(f'{API}/api/bot/students/test/results/{student.platform_id}')
    data = response.json()
    results = data.get('test_results', [])
    if not results:
        await message.answer("⚠️ Test natijalari topilmadi.")
        return

    text = f"📚 <b>{student.name}, test natijalari:</b>\n\n"
    for group in results:
        text += f"👥 Guruh: {group['name']}\n📚 Fan: {group['subject']}\n👨‍🏫 O‘qituvchi: {group['teacher']}\n"
        for result in group['tests']:
            text += f"📅 Sana: {result['date']} | ✅ {result['percentage']}%\n"
        text += "━" * 20 + "\n"
    await message.answer(text, parse_mode="HTML")


@student_router.message(F.text == "🖥️ Onlayn test natijalari")
async def online_results(message: Message):
    telegram_id = message.from_user.id
    student = get_student(telegram_id)
    response = requests.get(f'https://classroom.gennis.uz/api/pisa/student/pisa/results/{student.platform_id}')
    data = response.json()
    results = data.get('data', [])
    if not results:
        await message.answer("⚠️ Onlayn test natijalari topilmadi.")
        return

    text = f"💻 <b>{student.name}, onlayn test natijalari:</b>\n\n"
    for result in results:
        text += (
                f"📅 {result['test_date']}\n"
                f"📚 {result['pisa_name']}\n"
                f"✅ To‘g‘ri: {result['true_answers']}\n"
                f"❌ Noto‘g‘ri: {result['false_answers']}\n"
                f"📊 {result['result']}%\n"
                "━" * 20 + "\n"
        )
    await message.answer(text, parse_mode="HTML")


# ----------------------------- #
#      🧠 ONLAYN TEST BLOKI     #
# ----------------------------- #
@student_router.message(F.text == "🏁 Onlayn test yechish")
async def show_tests(message: Message, state: FSMContext):
    tests = get_tests()
    if not tests:
        await message.answer("🚫 Hozircha testlar mavjud emas.")
        return
    buttons = [[types.KeyboardButton(text=t["name"])] for t in tests]
    buttons.append([types.KeyboardButton(text="⬅️ Orqaga")])
    await message.answer("📋 Iltimos, testni tanlang:",
                         reply_markup=types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True))
    await state.update_data(tests=tests)


@student_router.message(StateFilter(None))
async def select_test(message: Message, state: FSMContext):
    if message.text == "⬅️ Orqaga":
        await message.answer("🔙 Orqaga qaytildi", reply_markup=student_basic_reply_keyboard_test_type())
        return

    data = await state.get_data()
    tests = data.get("tests", [])
    selected = next((t for t in tests if t["name"] == message.text), None)
    if not selected:
        return await message.answer("⚠️ Noto‘g‘ri tanlov.")

    await message.answer(f"✅ Siz tanladingiz: <b>{selected['name']}</b>", parse_mode="HTML")
    await message.answer("🧠 Test yuklanmoqda...", reply_markup=types.ReplyKeyboardRemove())

    test_url = f"https://classroom.gennis.uz/api/pisa/student/get/test/{selected['id']}"
    try:
        res = requests.get(test_url, headers={"Authorization": f"Bearer {GENNIS_TOKEN}"})
        test_data = res.json()
    except Exception as e:
        return await message.answer(f"❌ Xatolik: {e}")

    questions = []
    for block in test_data.get("pisa_blocks_right", []):
        options = block.get("answers", [])
        if options:
            questions.append({
                "text": block.get("q", "Savol topilmadi"),
                "answers": [{"text": o, "isTrue": idx == block.get("correct_answer_index", 0)} for idx, o in
                            enumerate(options)]
            })

    if not questions:
        await message.answer("⚠️ Savollar topilmadi.")
        return

    await state.update_data(question_number=0, score=0, questions=questions, test_id=selected["id"])
    await message.answer(f"📘 Test: <b>{selected['name']}</b>\n📄 Savollar soni: {len(questions)}", parse_mode="HTML")
    await state.set_state(TestStates.question_number)
    await send_question(message, state)


async def send_question(message: Message, state: FSMContext):
    data = await state.get_data()
    q_num = data.get("question_number", 0)
    questions = data.get("questions", [])

    if q_num >= len(questions):
        await finish_test(message, state)
        return

    q = questions[q_num]
    buttons = [[types.KeyboardButton(text=str(i + 1))] for i in range(len(q["answers"]))]
    buttons.append([types.KeyboardButton(text="❌ Testdan chiqish")])
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)

    await message.answer(
        f"{q['text']}\n\n" + "\n".join(f"{i + 1}. {a['text']}" for i, a in enumerate(q["answers"])),
        reply_markup=keyboard
    )

    progress_msg = await message.answer("⏳ 15s 【●●●●●●●●●●●●●●●】")
    task = asyncio.create_task(question_timer(message, state, q_num, progress_msg))
    await state.update_data(timer_task=task, waiting_answer=True)


async def question_timer(message: Message, state: FSMContext, q_num: int, progress_msg: types.Message):
    total_time = 15
    for remaining in range(total_time, 0, -1):
        try:
            bar = f"⏳ {remaining:02d}s 【{'●' * remaining}{'○' * (total_time - remaining)}】"
            await progress_msg.edit_text(bar)
        except Exception:
            pass
        await asyncio.sleep(1)

    data = await state.get_data()
    if data.get("waiting_answer") and data.get("question_number") == q_num:
        await message.answer("⌛️ Vaqt tugadi! Keyingi savolga o'tamiz.")
        await state.update_data(waiting_answer=False, question_number=q_num + 1)
        await send_question(message, state)


@student_router.message(TestStates.question_number, F.text == "❌ Testdan chiqish")
async def exit_test(message: Message, state: FSMContext):
    data = await state.get_data()
    timer_task = data.get("timer_task")
    if timer_task:
        timer_task.cancel()
    await state.clear()
    await message.answer("🚪 Testdan chiqdingiz.", reply_markup=student_basic_reply_keyboard_test_type())


@student_router.message(TestStates.question_number, F.text.regexp(r"^\d+$"))
async def answer_question(message: Message, state: FSMContext):
    data = await state.get_data()
    q_num = data.get("question_number", 0)
    score = data.get("score", 0)
    questions = data.get("questions", [])
    timer_task = data.get("timer_task")
    if timer_task:
        timer_task.cancel()

    q = questions[q_num]
    user_answer = int(message.text)
    correct_index = next((i + 1 for i, a in enumerate(q["answers"]) if a["isTrue"]), None)

    if user_answer == correct_index:
        score += 1
        await message.answer("✅ To‘g‘ri!")
    else:
        correct_text = q["answers"][correct_index - 1]["text"]
        await message.answer(f"❌ Noto‘g‘ri! To‘g‘ri javob: {correct_text}")

    await state.update_data(question_number=q_num + 1, score=score)
    await send_question(message, state)


async def finish_test(message: Message, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    total = len(data.get("questions", []))
    percent = round((score / total) * 100)
    test_id = data.get("test_id")

    save_result(message.from_user.id, message.from_user.username, score, total, percent)
    await message.answer(
        f"✅ Test tugadi!\nNatijangiz: {score}/{total} ({percent}%)",
        reply_markup=student_basic_reply_keyboard_test_type()
    )
    await state.clear()
