from app.handlers import router
from aiogram import F, types
from aiogram.filters import Command
from aiogram.types import Message
import requests
from app.models import User, Student, Teacher
from app.db import SessionLocal
import pprint
from .keyboards import create_years_reply_keyboard, create_months_inline_keyboard, student_basic_reply_keyboard

from app.keyboards import login_keyboard
from aiogram import Router

student_router = Router()
user_years_data = {}
user_months_data = {}
datas = {}
selected_year = {}
selected_month = {}


@student_router.message(F.text == "💳 To'lovlar ro‘yhati")
async def get_payments_list(message: Message):
    from run import api
    telegram_user = message.from_user
    telegram_id = telegram_user.id
    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        student = session.query(Student).filter(Student.user_id == get_user.id).first()
        response = requests.get(f'{api}/api/bot_student_payments/{student.platform_id}')
        payments = response.json().get('payments', [])

        if not payments:
            await message.answer("⚠️ To'lovlar topilmadi.")
            return

        # Build a table-like message
        text = f"📋 <b>{telegram_user.first_name}, so'nggi to'lovlar ro'yxati:</b>\n\n"
        text += "{:<15} {:<12} {:<10}\n".format("Sana", "Miqdor", "Turi")
        text += "-" * 40 + "\n"

        for pay in payments[:10]:  # show only first 10 payments for brevity
            text += "{:<5} {:<12} {:<10}\n".format(
                pay['date'],
                pay['amount'],
                pay['payment_type']
            )

        text += "\n⬆️ Qo'shimcha savollar uchun adminlarimizga murojaat qiling."

        await message.answer(text, parse_mode="HTML")


@student_router.message(F.text.startswith("🎯 Test natijalari"))
async def handle_test_results(message: Message):
    from run import api
    telegram_user = message.from_user
    telegram_id = message.from_user.id



    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        student = session.query(Student).filter(Student.user_id == get_user.id).first()

        response = requests.get(f'{api}/api/bot_student_test_results/{student.platform_id}')
        data = response.json()
        test_results = data.get('test_results', [])

        if not test_results:
            await message.answer("⚠️ Test natijalari topilmadi.")
            return

        text = f"📚 <b>{telegram_user.first_name},  test natijalari:</b>\n\n"
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
async def get_davomatlar_royxati(message: Message):
    from run import api
    telegram_user = message.from_user
    telegram_id = telegram_user.id

    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        student = session.query(Student).filter(Student.user_id == get_user.id).first()

        dates_response = requests.get(f'{api}/api/student_attendance_dates/{student.platform_id}')
        dates_data = dates_response.json()['data']
        user_years_data[telegram_id] = dates_data['years']
        user_months_data[telegram_id] = dates_data['months']
        datas[telegram_id] = dates_data

        years_keyboard = create_years_reply_keyboard(dates_data)
        await message.answer("✅ Yilni tanlang:", reply_markup=years_keyboard)


@student_router.message(lambda message: message.text in user_years_data.get(message.from_user.id, []))
async def handle_dynamic_year_selection(message: Message):
    telegram_id = message.from_user.id
    year = message.text
    await message.answer(f"✅ Siz {year} yilni tanladingiz!")
    selected_year[telegram_id] = year
    months_keyboard = create_months_inline_keyboard(datas.get(telegram_id), selected_year[telegram_id])
    await message.answer("✅ Shu yilning oylarini tanlang:", reply_markup=months_keyboard)


@student_router.callback_query(lambda c: c.data.startswith("month_"))
async def handle_month_selection(callback: types.CallbackQuery):
    from run import api
    telegram_user = callback.message.from_user
    telegram_id = callback.from_user.id
    month = callback.data.split("_")[1]
    await callback.message.answer(f"✅ Siz {month} oyini tanladingiz!")
    selected_month[telegram_id] = month
    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        student = session.query(Student).filter(Student.user_id == get_user.id).first()
    response = requests.get(
        f'{api}/api/bot_student_attendances/{student.platform_id}/{selected_year[telegram_id]}/{selected_month[telegram_id]}')
    tables = response.json()['attendances']

    if not tables:
        await callback.message.answer("⚠️ Davomat topilmadi.")
        return
    text = f"📅 <b>{telegram_user.first_name}, sizning davomat jadvalingiz:</b>\n\n"

    for table in tables:
        text += f"🔷 <b>{table['subject']} ({table['name']})</b>\n"
        text += f"👨‍🏫 O'qituvchi: <i>{table['teacher']}</i>\n"
        text += "📚 <b>Darslar:</b>\n"

        for attendance in table['attendances']:
            if attendance['ball_status'] == 1 or attendance['ball_status'] == 2:
                text += f"  🔹 <b>{attendance['day']}</b> ✅ \n"
            else:
                text += f"  🔹 <b>{attendance['day']}</b> ❌ \n"
            if attendance['ball_status'] == 2:
                if attendance['dictionary']:
                    text += (
                        f"    📌 <b>Uy ishi:</b> {attendance['homework']}\n"
                        f"    📖 <b>Lug'at:</b> {attendance['dictionary']}\n"
                        f"    🎯 <b>Aktiv:</b> {attendance['activeness']}\n"
                    )
                else:
                    text += (
                        f"    📌 <b>Uy ishi:</b> {attendance['homework']}\n"
                        f"    🎯 <b>Aktiv:</b> {attendance['activeness']}\n"
                    )

        text += "━" * 25 + "\n\n"

    await callback.message.answer(text, parse_mode="HTML")

    months_keyboard = create_months_inline_keyboard(datas.get(telegram_id), selected_year[telegram_id])
    await callback.message.answer("✅ Yana oy tanlang:", reply_markup=months_keyboard)
