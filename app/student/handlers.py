import requests
import asyncio
import pprint
import requests
import functools
import json
import time
import os

from aiogram import F, types
from aiogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from .keyboards import create_years_reply_keyboard, create_months_inline_keyboard, student_basic_reply_keyboard, \
    student_basic_reply_keyboard_test_type
from dotenv import load_dotenv
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import Router
from aiogram.filters import StateFilter
from app.states import MenuStates, TestStates
from .utils import get_student
from app.models import TestResult, User
from app.db import SessionLocal, Base
from utils import timer_tasks, progress_messages, QUESTION_TIME, safe_get, safe_post, get_platform_id

student_router = Router()
years_data = {}
dates_info = {}

selected_student_year = {}
selected_student_month = {}
user_mode = {}
load_dotenv()

timer_tasks = {}


@student_router.message(F.text == "💳 To'lovlar ro‘yhati")
async def get_payments_list(message: Message):
    api = os.getenv('API')
    telegram_user = message.from_user
    telegram_id = telegram_user.id

    student = get_student(telegram_id)
    response = requests.get(f'{api}/api/bot/students/payments/{student.platform_id}')
    payments = response.json().get('payments', [])

    if not payments:
        await message.answer("⚠️ To'lovlar topilmadi.")
        return

    # Build a table-like message
    text = f"📋 <b>{student.name}, so'nggi to'lovlar ro'yxati:</b>\n\n"
    text += "{:<15} {:<12} {:<10}\n".format("Sana", "Miqdor", "Turi")
    text += "-" * 40 + "\n"

    for pay in payments:  # show only first 10 payments for brevity
        text += "{:<5} {:<12} {:<10}\n".format(
            pay['date'],
            pay['amount'],
            pay['payment_type']
        )

    text += "\n⬆️ Qo'shimcha savollar uchun adminlarimizga murojaat qiling."

    await message.answer(text, parse_mode="HTML")


@student_router.message(F.text.startswith("🎯 Test natijalari"))
async def test_types(message: Message):
    await message.answer(
        "👆 Iltimos, quyidagilardan birini tanlang:",
        reply_markup=student_basic_reply_keyboard_test_type
    )


@student_router.message(F.text == "📄 Offlayn test natijalari")
async def handle_test_results(message: Message):
    api = os.getenv('API')
    telegram_id = message.from_user.id
    student = get_student(telegram_id)
    response = requests.get(f'{api}/api/bot/students/test/results/{student.platform_id}')
    data = response.json()
    test_results = data.get('test_results', [])

    if not test_results:
        await message.answer("⚠️ Test natijalari topilmadi.")
        return

    text = f"📚 <b>{student.name},  test natijalari:</b>\n\n"
    for group in test_results:
        group_name = group['name']
        subject_name = group['subject']
        teacher = group['teacher']
        tests = group['tests']

        text += (
            f"👥 <b>Guruh:</b> {group_name}\n"
            f"📚 <b>Fan:</b> {subject_name}\n"
            f"👨‍🏫 <b>O'qituvchi:</b> {teacher}\n"
        )

        if not tests:
            text += "⚠️ Test natijalari yo'q.\n"
        else:
            for result in tests:
                text += (
                    f"📅 <b>Sana:</b> {result['date']}\n"
                    f"✅ <b>Natija:</b> {result['percentage']} "
                    f"({result['true_answers']} ta to'g'ri javob)\n"
                    f"🎯 <b>Test:</b> {result['test_info']['name']} "
                    f"(Daraja: {result['test_info']['level']})\n"
                )
                text += "━" * 20 + "\n"

        text += "═" * 25 + "\n\n"

    await message.answer(text, parse_mode="HTML")


@student_router.message(F.text == "🖥️ Onlayn test natijalari")
async def handle_online_test_results(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    platform_id = get_platform_id(telegram_id)
    if not platform_id:
        await message.answer("❌ Пользователь не найден в базе.")
        return
    api_url = f"https://classroom.gennis.uz/api/pisa/student/get/list_bot/{platform_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as e:
        await message.answer(f"❌ Xatolik yuz berdi: {e}")
        return
    except json.JSONDecodeError:
        await message.answer("❌ Xato: server noto‘g‘ri JSON yubordi.")
        return
    finished_tests = [t for t in data if t.get("finished")]
    if not finished_tests:
        await message.answer("⚠️ Sizda yakunlangan testlar topilmadi.")
        return
    buttons = []
    for t in finished_tests:
        pisa_id = t.get("id")
        buttons.append(
            [InlineKeyboardButton(text=t.get("name", "Test"), callback_data=f"online_test_{pisa_id}")]
        )
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    sent_msg = await message.answer("📋 Iltimos, yakunlangan testlardan birini tanlang:", reply_markup=keyboard)
    await state.update_data(finished_tests=finished_tests, last_message_id=sent_msg.message_id)


@student_router.callback_query(lambda c: c.data.startswith("online_test_"))
async def show_selected_online_test(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    pisa_id = int(callback.data.split("_")[-1])
    telegram_id = callback.from_user.id
    platform_id = get_platform_id(telegram_id)
    if not platform_id:
        await callback.message.edit_text("❌ Sizning hisobingiz topilmadi.")
        return
    api_url = f"https://classroom.gennis.uz/api/pisa/student/show/result_bot/{pisa_id}/{platform_id}"
    try:
        resp = await safe_get(api_url)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik yuz berdi: {e}")
        return
    result = data.get("test", {})
    text = (
        f"💻 <b>{callback.from_user.full_name}, onlayn test natijalari:</b>\n\n"
        f"📅 <b>Sana:</b> {result.get('test_date', 'N/A')}\n"
        f"📚 <b>Test nomi:</b> {result.get('pisa_name', 'N/A')}\n"
        f"✅ <b>To‘g‘ri javoblar:</b> {result.get('true_answers', 0)} ta\n"
        f"❌ <b>Noto‘g‘ri javoblar:</b> {result.get('false_answers', 0)} ta\n"
        f"📊 <b>Natija:</b> {result.get('result', 0)}%\n"
        f"📋 <b>Savollar soni:</b> {result.get('total_questions', 0)} ta\n"
    )
    back_button = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="⬅️ Orqaga", callback_data="back_to_tests")]]
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=back_button)


@student_router.callback_query(F.data == "back_to_tests")
async def back_to_tests(callback: types.CallbackQuery, state: FSMContext):
    await callback.answer()
    telegram_id = callback.from_user.id
    platform_id = get_platform_id(telegram_id)
    if not platform_id:
        await callback.message.edit_text("❌ Sizning hisobingiz topilmadi.")
        return
    api_url = f"https://classroom.gennis.uz/api/pisa/student/get/list_bot/{platform_id}"
    try:
        response = requests.get(api_url, timeout=10)
        response.raise_for_status()
        data = response.json()
    except Exception as e:
        await callback.message.edit_text(f"❌ Xatolik yuz berdi: {e}")
        return
    finished_tests = [t for t in data if t.get("finished")]
    if not finished_tests:
        await callback.message.edit_text("⚠️ Sizda yakunlangan testlar topilmadi.")
        return
    buttons = []
    for t in finished_tests:
        pisa_id = t.get("id")
        buttons.append(
            [InlineKeyboardButton(text=t.get("name", "Test"), callback_data=f"online_test_{pisa_id}")]
        )
    keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
    await callback.message.edit_text(
        "📋 Iltimos, yakunlangan testlardan birini tanlang:",
        reply_markup=keyboard
    )


@student_router.message(StateFilter("*"), F.text == "⬅️ Orqaga")
async def back_to_menu(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👆 Iltimos, quyidagilardan birini tanlang:",
        reply_markup=student_basic_reply_keyboard_test_type
    )


@student_router.message(F.text == "🏁 Onlayn test yechish")
async def show_tests(message: types.Message, state: FSMContext):
    telegram_id = message.from_user.id
    platform_id = get_platform_id(telegram_id)
    if not platform_id:
        await message.answer("❌ Sizning hisobingiz topilmadi.")
        return
    api_url = f"https://classroom.gennis.uz/api/pisa/student/get/list_bot/{platform_id}"
    try:
        resp = await safe_get(api_url)
        resp.raise_for_status()
        tests = resp.json()
    except Exception as e:
        await message.answer(f"❌ Xatolik: {e}")
        return
    if not isinstance(tests, list):
        await message.answer("⚠️ Server noto‘g‘ri format yubordi (kutilgan list).")
        return
    available_tests = [t for t in tests if not t.get("finished", False)]
    if not available_tests:
        await message.answer("✅ Siz barcha testlarni yakunlagansiz!")
        await state.clear()
        return
    buttons = [[types.KeyboardButton(text=t["name"])] for t in available_tests]
    buttons.append([types.KeyboardButton(text="⬅️ Orqaga")])
    keyboard = types.ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
    await state.update_data(tests=available_tests)
    await message.answer("📋 Iltimos, testni tanlang:", reply_markup=keyboard)


@student_router.message(StateFilter(None))
async def select_test(message: types.Message, state: FSMContext):
    if message.text in ("⬅️ Orqaga", "📊 Natijalarni ko‘rish", "🏁 Testni boshlash", "ℹ️ Yordam"):
        if message.text == "⬅️ Orqaga":
            await message.answer("👆 Iltimos, quyidagilardan birini tanlang:",
                                 reply_markup=student_basic_reply_keyboard_test_type)
        return
    data = await state.get_data()
    telegram_id = message.from_user.id
    platform_id = get_platform_id(telegram_id)
    if not platform_id:
        await message.answer("❌ Sizning hisobingiz topilmadi.")
        return
    tests = data.get("tests", [])
    selected = next((t for t in tests if t["name"] == message.text), None)
    if not selected:
        return
    await message.answer(f"✅ Siz tanladingiz: <b>{selected['name']}</b>", parse_mode="HTML")
    await message.answer("🧠 Test yuklanmoqda...", reply_markup=types.ReplyKeyboardRemove())
    test_url = f"https://classroom.gennis.uz/api/pisa/student/get/test_bot/{selected['id']}/{platform_id}"
    try:
        response = requests.get(test_url)  # headers=headers
    except Exception as e:
        await message.answer(f"🚫 So‘rovda xatolik: {e}")
        return
    if response.status_code != 200 or not response.text.strip():
        await message.answer(f"⚠️ Server xatosi ({response.status_code}) yoki bo‘sh javob.")
        return
    try:
        test_data = response.json()
    except json.JSONDecodeError:
        await message.answer("⚠️ Server noto‘g‘ri JSON yubordi.")
        return
    questions = []
    for block in test_data.get("pisa_blocks_right", []):
        if block.get("innerType") == "text" and block.get("options"):
            answers = [{"text": opt.get("text"), "isTrue": opt.get("isTrue")} for opt in block["options"]]
            questions = []
            for block in test_data.get("pisa_blocks_right", []):
                if block.get("innerType") == "text" and block.get("options"):
                    answers = [
                        {
                            "id": opt.get("id"),
                            "text": opt.get("text"),
                            "isTrue": opt.get("isTrue")
                        }
                        for opt in block["options"]
                    ]
                    questions.append({
                        "id": block["id"],
                        "text": block.get("text", "Savol topilmadi"),
                        "answers": answers
                    })
    if not questions:
        await message.answer("❗️ Bu testda savollar topilmadi yoki noto‘g‘ri formatda.",
                             reply_markup=student_basic_reply_keyboard_test_type)
        return
    await state.update_data(question_number=0, score=0, questions=questions, test_id=selected["id"])
    await message.answer(
        f"📘 Test: <b>{selected['name']}</b>\n"
        f"📄 Savollar soni: {len(questions)}\n\n"
        "Boshlaymiz! 💪",
        parse_mode="HTML"
    )
    await state.set_state(TestStates.question_number)
    await send_question(message, state)


async def send_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_num = data.get("question_number", 0)
    questions = data.get("questions", [])
    chat_id = message.chat.id
    prev_task = timer_tasks.get(chat_id)
    if prev_task and not prev_task.done():
        prev_task.cancel()
    if q_num >= len(questions):
        await finish_test(message, state)
        return
    q = questions[q_num]
    options = q.get("answers", [])
    question_text = q.get("text", "Savol topilmadi")
    options_text = "\n".join(f"{i + 1}. {opt['text']}" for i, opt in enumerate(options))
    sent = await message.answer(f"{question_text}\n\n{options_text}",
                                reply_markup=types.ReplyKeyboardMarkup(
                                    keyboard=[[types.KeyboardButton(text=str(i + 1))] for i in range(len(options))] + [
                                        [types.KeyboardButton(text="❌ Testdan chiqish")]],
                                    resize_keyboard=True
                                )
                                )
    progress_msg = await message.answer(f"⏳ {QUESTION_TIME:02d}s 【{'●' * QUESTION_TIME}】")
    progress_messages[chat_id] = {"progress_id": progress_msg.message_id, "question_message_id": sent.message_id}
    task = asyncio.create_task(question_timer(message, state, q_num, progress_msg.message_id))
    timer_tasks[chat_id] = task
    await state.update_data(waiting_answer=True)


async def question_timer(message: types.Message, state: FSMContext, q_num: int, progress_message_id: int):
    chat_id = message.chat.id
    total_time = QUESTION_TIME
    try:
        for remaining in range(total_time, 0, -1):
            bar = f"⏳ {remaining:02d}s 【{'●' * remaining}{'○' * (total_time - remaining)}】"
            try:
                await message.bot.edit_message_text(bar, chat_id=chat_id, message_id=progress_message_id)
            except Exception:
                pass
            await asyncio.sleep(1)
        data = await state.get_data()
        if data.get("waiting_answer") and data.get("question_number") == q_num:
            try:
                await message.bot.send_message(chat_id, "⌛️ Vaqt tugadi! Keyingi savolga o'tamiz.")
            except Exception:
                pass
            await state.update_data(waiting_answer=False, question_number=q_num + 1)
            progress_messages.pop(chat_id, None)
            timer_tasks.pop(chat_id, None)
            await asyncio.sleep(0.5)
            await send_question(message, state)
    except asyncio.CancelledError:
        return


@student_router.message(TestStates.question_number, F.text == "❌ Testdan chiqish")
async def exit_test(message: types.Message, state: FSMContext):
    chat_id = message.chat.id
    task = timer_tasks.get(chat_id)
    if task and not task.done():
        task.cancel()
    timer_tasks.pop(chat_id, None)
    progress_messages.pop(chat_id, None)
    await state.clear()
    await message.answer("🚪 Siz testdan chiqdingiz.", reply_markup=student_basic_reply_keyboard_test_type)


@student_router.message(TestStates.question_number, F.text.regexp(r"^\d+$"))
async def answer_question(message: types.Message, state: FSMContext):
    data = await state.get_data()
    q_num = data.get("question_number", 0)
    score = data.get("score", 0)
    questions = data.get("questions", [])
    chat_id = message.chat.id
    prev_task = timer_tasks.get(chat_id)
    if prev_task and not prev_task.done():
        prev_task.cancel()
    if q_num >= len(questions):
        await finish_test(message, state)
        return
    q = questions[q_num]
    options = q.get("answers", [])
    user_answer = int(message.text)
    if 1 <= user_answer <= len(options):
        correct_index = next((i + 1 for i, a in enumerate(options) if a.get("isTrue")), None)
        user_answers = data.get("user_answers", {})
        block_id = q["id"]
        answer_id = options[user_answer - 1]["id"]
        user_answers[block_id] = {
            "block_id": block_id,
            "type": "select",
            "answer": {"id": answer_id}
        }
        await state.update_data(user_answers=user_answers)
        await state.update_data(waiting_answer=False)
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


async def finish_test(message: types.Message, state: FSMContext):
    data = await state.get_data()
    user_answers = data.get("user_answers", {})
    test_id = data.get("test_id")
    score = data.get("score", 0)
    questions = data.get("questions", [])
    total = len(questions)
    percent = round((score / total) * 100) if total else 0
    if not test_id:
        await message.answer("❌ Test ID topilmadi.")
        return
    telegram_id = message.from_user.id
    platform_id = get_platform_id(telegram_id)
    if not platform_id:
        await message.answer("❌ Sizning hisobingiz topilmadi.")
        return
    for answer_object in user_answers.values():
        complete_url = f"https://classroom.gennis.uz/api/pisa/student/complete/pisa/test_bot/{test_id}/{platform_id}"
        resp = await safe_post(
            complete_url,
            json_payload=answer_object,
            headers={
                "Accept": "application/json",
                "Content-Type": "application/json"
            }
        )
        if resp.status_code != 200:
            await message.answer(f"⚠️ Xatolik: {resp.status_code}")
            return
    show_url = f"https://classroom.gennis.uz/api/pisa/student/show/result_bot/{test_id}/{platform_id}"
    try:
        result_resp = await safe_get(show_url)
        result_resp.raise_for_status()
        result_data = result_resp.json()
    except Exception as e:
        await message.answer(f"⚠️ Xatolik olishda natijalar: {e}")
        result_data = {}
    await message.answer("✅ Test muvaffaqiyatli yakunlandi!")
    await message.answer(
        f"🏁 Test tugadi!\n"
        f"To‘g‘ri javoblar: {score}/{total}\n"
        f"Foiz: {percent}%",
        reply_markup=student_basic_reply_keyboard_test_type
    )
    chat_id = message.chat.id
    task = timer_tasks.pop(chat_id, None)
    if task and not task.done():
        task.cancel()
    progress_messages.pop(chat_id, None)
    await state.clear()


@student_router.message(F.text == "📝 Davomatlar ro‘yhati")
async def get_davomatlar_royxati(message: Message, state: FSMContext):
    api = os.getenv('API')
    await state.set_state(MenuStates.attendances)

    telegram_id = message.from_user.id
    student = get_student(telegram_id)
    response = requests.get(f'{api}/api/bot/students/attendance/dates/{student.platform_id}')
    dates_data = response.json()['data']

    await state.update_data(
        mode="attendance",
        years=dates_data['years'],
        dates_info=dates_data,
        selected_year=None,
        selected_month=None
    )

    years_keyboard = create_years_reply_keyboard(dates_data)
    await message.answer("✅ Yilni tanlang:", reply_markup=years_keyboard)


@student_router.message(lambda msg: msg.text and "baholar" in msg.text.lower())
async def get_baholar(message: Message, state: FSMContext):
    api = os.getenv('API')
    await state.set_state(MenuStates.scores)

    telegram_id = message.from_user.id
    student = get_student(telegram_id)
    response = requests.get(f'{api}/api/bot/students/attendance/dates/{student.platform_id}')
    dates_data = response.json()['data']

    await state.update_data(
        mode="scores",
        years=dates_data['years'],
        dates_info=dates_data,
        selected_year=None,
        selected_month=None
    )

    years_keyboard = create_years_reply_keyboard(dates_data)
    await message.answer("✅ Yilni tanlang:", reply_markup=years_keyboard)


@student_router.message(StateFilter(MenuStates.attendances, MenuStates.scores))
async def handle_dynamic_year_selection(message: Message, state: FSMContext):
    data = await state.get_data()
    if not data.get("years"):
        return

    if message.text in data["years"]:
        await state.update_data(selected_year=message.text)

        months_keyboard = create_months_inline_keyboard(
            data["dates_info"], message.text
        )
        await message.answer(f"✅ Siz {message.text} yilni tanladingiz!")
        await message.answer("✅ Shu yilning oylarini tanlang:", reply_markup=months_keyboard)


@student_router.callback_query(lambda c: c.data.startswith("month_"))
async def handle_month_selection(callback: types.CallbackQuery, state: FSMContext):
    api = os.getenv("API")
    telegram_id = callback.from_user.id
    month = callback.data.split("_")[1]

    await callback.message.answer(f"✅ Siz {month} oyini tanladingiz!")
    data = await state.get_data()
    await state.update_data(selected_month=month)

    student = get_student(telegram_id)
    year = data.get("selected_year")
    mode = data.get("mode")

    if mode == "attendance":
        response = requests.get(f'{api}/api/bot/students/attendances/{student.platform_id}/{year}/{month}')
        tables = response.json().get("attendances", [])

        if not tables:
            await callback.message.answer("⚠️ Davomat topilmadi.")
            return

        text = f"📅 <b>{student.name}, sizning davomat jadvalingiz:</b>\n\n"
        for table in tables:
            text += f"🔷 <b>{table['subject']} ({table['name']})</b>\n"
            text += f"👨‍🏫 O'qituvchi: <i>{table['teacher']}</i>\n📚 <b>Darslar:</b>\n"
            for attendance in table['attendances']:
                status_icon = "✅" if attendance["ball_status"] in [1, 2] else "❌"
                text += f"  🔹 <b>{attendance['day']}</b> {status_icon}\n"
                if attendance["ball_status"] == 2:
                    text += f"    📌 Uy ishi: {attendance['homework']}\n"
                    if attendance.get("dictionary"):
                        text += f"    📖 Lug'at: {attendance['dictionary']}\n"
                    text += f"    🎯 Aktivlik: {attendance['activeness']}\n"
            text += "━" * 25 + "\n\n"
        await callback.message.answer(text, parse_mode="HTML")

    else:  # scores mode
        response = requests.get(f'{api}/api/bot/students/scores/{student.platform_id}/{year}/{month}')
        tables = response.json().get("score_list", [])

        if not tables:
            await callback.message.answer("⚠️ Baholar topilmadi.")
            return

        text = f"📊 <b>{student.name}, {month} oyidagi baholar:</b>\n\n"
        for table in tables:
            text += f"🔷 <b>{table['subject']} ({table['name']})</b>\n"
            text += f"👨‍🏫 O'qituvchi: <i>{table['teacher']}</i>\n"
            text += f"📈 O'rtacha ball: <b>{table['average_ball']}</b>\n"

            if not table['score']:
                text += "⚠️ Baholar mavjud emas.\n"
            else:
                text += "📚 <b>Darslar bo‘yicha baholar:</b>\n"
                for score in table['score']:
                    text += f"  🔹 <b>{score['day']}</b> ✅\n"
                    text += f"    📌 Uy ishi: {score['homework']}\n"
                    text += f"    🎯 Aktivlik: {score['activeness']}\n"
                    if table.get("dictionary_status"):
                        text += f"    📖 Lug‘at: {score['dictionary']}\n"
            text += "━" * 25 + "\n\n"

        await callback.message.answer(text, parse_mode="HTML")

    months_keyboard = create_months_inline_keyboard(
        data["dates_info"], data["selected_year"]
    )
    await callback.message.answer("✅ Yana oy tanlang:", reply_markup=months_keyboard)
