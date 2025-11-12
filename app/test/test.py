import os
import asyncio
import requests
from aiogram import Router, types, F
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

student_router = Router()

GENNIS_TOKEN = os.getenv(
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJmcmVzaCI6ZmFsc2UsImlhdCI6MTc2Mjg1NjY4NCwianRpIjoiYmFhZTczZTAtNmU4Yy00NDU1LWEwYTktNGU4NjYzMzhiNjY5IiwidHlwZSI6ImFjY2VzcyIsInN1YiI6IjhkMDI3NzJjNTE5MzExZjBhNTQ4MzFkODQyNzBhMjIwIiwibmJmIjoxNzYyODU2Njg0LCJjc3JmIjoiZmY2OGFkZDktNGEyOS00OGZiLWFmMzEtMDFjZDliNmE2ZGVhIiwiZXhwIjoxNzYyOTQzMDg0fQ.kyqMRFUS8AcPDqMJ8yLD0duqw0Q0wwiGgGgAkcfdKlc")
TEST_LIST_URL = "https://classroom.gennis.uz/api/pisa/test/crud/34"
active_questions = {}
HEADERS = lambda token: {
    "Authorization": f"Bearer {token}",
    "Accept": "application/json",
    "User-Agent": "GennisBot/1.0"
}
# ----- STATE -----
class TestStates(StatesGroup):
    question_number = State()
    score = State()
    questions = State()
    waiting_answer = State()
    test_id = State()
    timer_task = State()


# ----- HELPERS -----
def save_result(user_id, username, score, total, percent):
    # Bu yerda SQLAlchemy yoki boshqa DB kodini qo‘shish mumkin
    print(f"Natija saqlandi: {user_id}, {username}, {score}/{total} ({percent}%)")


def student_basic_reply_keyboard_test_type():
    return types.ReplyKeyboardMarkup(
        keyboard=[
            [types.KeyboardButton(text="🏁 Onlayn test yechish")],
            [types.KeyboardButton(text="⬅️ Orqaga")]
        ],
        resize_keyboard=True
    )


def get_tests():
    url = "https://classroom.gennis.uz/api/pisa/test/crud/34"
    headers = {"Authorization": f"Bearer {GENNIS_TOKEN}"}
    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if isinstance(data, dict):
            return [{"id": data.get("id", 34), "name": data.get("name", "Nomaʼlum test")}]
        elif isinstance(data, list):
            return [{"id": t["id"], "name": t["name"]} for t in data if "id" in t and "name" in t]
    except Exception as e:
        print(f"Xatolik test olishda: {e}")
    return []


# ----- NAVIGATION -----
@student_router.message(F.text == "⬅️ Orqaga")
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👆 Iltimos, quyidagilardan birini tanlang:",
        reply_markup=student_basic_reply_keyboard_test_type()
    )


@student_router.message(F.text == "🏁 Onlayn test yechish")
async def show_tests(message: types.Message, state: FSMContext):
    tests = get_tests()
    if not tests:
        await message.answer("🚫 Hozircha testlar mavjud emas.")
        return
    buttons = [[types.KeyboardButton(text=t["name"])] for t in tests]
    buttons.append([types.KeyboardButton(text="⬅️ Orqaga")])
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer("📋 Iltimos, testni tanlang:", reply_markup=keyboard)
    await state.update_data(tests=tests)


@student_router.message(StateFilter(None))
async def select_test(message: types.Message, state: FSMContext):
    if message.text in ("⬅️ Orqaga",):
        return
    data = await state.get_data()
    tests = data.get("tests", [])
    selected = next((t for t in tests if t["name"] == message.text), None)
    if not selected:
        return

    await message.answer(f"✅ Siz tanladingiz: <b>{selected['name']}</b>", parse_mode="HTML")
    await message.answer("🧠 Test yuklanmoqda...", reply_markup=types.ReplyKeyboardRemove())
    test_url = f"https://classroom.gennis.uz/api/pisa/student/get/test/{selected['id']}"
    try:
        response = requests.get(test_url, headers={"Authorization": f"Bearer {GENNIS_TOKEN}"})
        test_data = response.json()
    except Exception as e:
        await message.answer(f"🚫 So‘rovda xatolik: {e}")
        return

    questions = []
    for block in test_data.get("pisa_blocks_right", []):
        # Agar variantlar mavjud bo'lsa
        options = block.get("answers", [])
        if options:
            questions.append({
                "id": block.get("id"),
                "text": block.get("q", "Savol matni mavjud emas"),
                "answers": [{"text": o, "isTrue": idx == block.get("correct_answer_index", 0)} for idx, o in enumerate(options)]
            })

    if not questions:
        await message.answer("❗️ Bu testda savollar topilmadi yoki noto‘g‘ri formatda.",
                             reply_markup=student_basic_reply_keyboard_test_type())
        return

    await state.update_data(question_number=0, score=0, questions=questions, test_id=selected["id"])
    await message.answer(
        f"📘 Test: <b>{selected['name']}</b>\n📄 Savollar soni: {len(questions)}\n\nBoshlaymiz! 💪",
        parse_mode="HTML"
    )
    await state.set_state(TestStates.question_number)
    await send_question(message, state)


# ----- SEND QUESTION -----
async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_num = data.get("question_number", 0)
    questions = data.get("questions", [])
    prev_task = data.get("timer_task")
    if prev_task and not prev_task.done():
        prev_task.cancel()

    if q_num >= len(questions):
        await finish_test(message, state)
        return

    q = questions[q_num]
    options = q.get("answers", [])
    question_text = q.get("text", "Savol topilmadi")
    buttons = [[types.KeyboardButton(text=str(i + 1))] for i in range(len(options))]
    buttons.append([types.KeyboardButton(text="❌ Testdan chiqish")])
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await message.answer(
        f"{question_text}\n\n" + "\n".join(f"{i + 1}. {opt['text']}" for i, opt in enumerate(options)),
        reply_markup=keyboard
    )

    progress_msg = await message.answer("⏳ 15s 【●●●●●●●●●●●●●●●】")
    task = asyncio.create_task(question_timer(message, state, q_num, progress_msg))
    await state.update_data(timer_task=task, waiting_answer=True)


async def question_timer(message: types.Message, state: FSMContext, q_num: int, progress_msg: types.Message):
    total_time = 15
    try:
        for remaining in range(total_time, 0, -1):
            bar = f"⏳ {remaining:02d}s 【{'●' * remaining}{'○' * (total_time - remaining)}】"
            try:
                await progress_msg.edit_text(bar)
            except Exception:
                pass
            await asyncio.sleep(1)
        data = await state.get_data()
        if data.get("waiting_answer") and data.get("question_number") == q_num:
            await message.answer("⌛️ Vaqt tugadi! Keyingi savolga o'tamiz.")
            await state.update_data(waiting_answer=False, question_number=q_num + 1)
            await asyncio.sleep(0.5)
            await send_question(message, state)
    except asyncio.CancelledError:
        return


# ----- ANSWER HANDLER -----
@student_router.message(TestStates.question_number, F.text == "❌ Testdan chiqish")
async def exit_test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    timer_task = data.get("timer_task")
    if timer_task:
        timer_task.cancel()
    await state.clear()
    await message.answer("🚪 Siz testdan chiqdingiz.", reply_markup=student_basic_reply_keyboard_test_type())


@student_router.message(TestStates.question_number, F.text.regexp(r"^\d+$"))
async def answer_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_num = data.get("question_number", 0)
    score = data.get("score", 0)
    questions = data.get("questions", [])
    timer_task = data.get("timer_task")
    if timer_task:
        timer_task.cancel()

    if q_num >= len(questions):
        await finish_test(message, state)
        return

    q = questions[q_num]
    options = q.get("answers", [])
    user_answer = int(message.text)
    correct_index = next((i + 1 for i, a in enumerate(options) if a.get("isTrue")), None)

    await state.update_data(waiting_answer=False)

    if 1 <= user_answer <= len(options):
        if user_answer == correct_index:
            score += 1
            await message.answer("✅ To‘g‘ri!")
        else:
            correct_text = options[correct_index - 1]["text"] if correct_index else "?"
            await message.answer(f"❌ Noto‘g‘ri!\nTo‘g‘ri javob: {correct_text}")
        await state.update_data(question_number=q_num + 1, score=score)
        await send_question(message, state)
    else:
        await message.answer("⚠️ Iltimos, to‘g‘ri raqamni tanlang.")


# ----- FINISH TEST -----
async def finish_test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    score = data.get("score", 0)
    total = len(data.get("questions", []))
    percent = round((score / total) * 100) if total else 0
    test_id = data.get("test_id")
    save_result(
        user_id=message.from_user.id,
        username=message.from_user.username,
        score=score,
        total=total,
        percent=percent
    )

    # API ga yuborish
    if test_id:
        try:
            api_url = f"https://classroom.gennis.uz/api/student/complete/pisa/test/{test_id}"
            payload = {
                "telegram_id": message.from_user.id,
                "score": score,
                "percent": percent
            }
            headers = {
                "Authorization": f"Bearer {API_TOKEN}",
                "Content-Type": "application/json"
            }
            response = requests.post(api_url, json=payload, headers=headers)
            if response.status_code == 200:
                print("✅ Natija serverga yuborildi")
            else:
                print(f"⚠️ Server javobi: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"❌ API yuborishda xato: {e}")

    await message.answer(
        f"✅ Test tugadi!\nSiz {score}/{total} to‘g‘ri javob berdingiz.\n📊 Foiz: {percent}%",
        reply_markup=student_basic_reply_keyboard_test_type()
    )
    await state.clear()
