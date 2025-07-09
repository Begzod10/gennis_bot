from aiogram import F, types
from aiogram.types import Message
import requests
import pprint
from .keyboards import create_years_reply_keyboard, create_months_inline_keyboard, student_basic_reply_keyboard
import os
from dotenv import load_dotenv
from aiogram.fsm.context import FSMContext
from aiogram import Router
from aiogram.filters import StateFilter
from app.states import MenuStates
from .utils import get_student

student_router = Router()
years_data = {}
dates_info = {}

selected_student_year = {}
selected_student_month = {}
user_mode = {}
load_dotenv()


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
