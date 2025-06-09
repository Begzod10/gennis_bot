from app.handlers import router
from aiogram import Router, F, types
from aiogram.filters import Command
from aiogram.types import Message
import requests
from app.models import User, Teacher
from app.db import SessionLocal
import pprint
from .keyboards import teacher_basic_reply_keyboard, teacher_years_keyboard
from aiogram import Router

teacher_router = Router()
teacher_years_data = {}
selected_year = {}


@teacher_router.message(F.text == "💳 Oyliklar ro‘yhati")
async def get_oyliklar_royxati(message: Message):
    from run import api
    telegram_user = message.from_user
    telegram_id = telegram_user.id

    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        teacher = session.query(Teacher).filter(Teacher.user_id == get_user.id).first()

        response = requests.get(f'{api}/api/bot_teacher_salary_years/{teacher.platform_id}')
        data = response.json()
        pprint.pprint(data)
        years = data.get('years', [])
        teacher_years_data[telegram_id] = years
        print("Stored years for user:", teacher_years_data.get(message.from_user.id, []))

    await message.answer("✅ Yilni tanlang:", reply_markup=await teacher_years_keyboard(years))


@teacher_router.message(lambda message: message.text.strip() in teacher_years_data.get(message.from_user.id, []))
async def handle_dynamic_year_selection(message: Message):
    from run import api  # Use separate config to avoid circular imports
    telegram_id = message.from_user.id
    year = message.text.strip()
    await message.answer(f"✅ Siz {year} yilni tanladingiz!")
    selected_year[telegram_id] = year

    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        teacher = session.query(Teacher).filter(Teacher.user_id == get_user.id).first()

        response = requests.get(f'{api}/api/bot_teacher_salary/{teacher.platform_id}/{year}')
        data = response.json()

        if not data or not data[0].get('salary_list'):
            await message.answer("⚠️ Bu yil uchun oylik ma'lumotlari topilmadi.")
            return

        teacher_info = data[0]
        salary_list = teacher_info['salary_list']

        full_name = f"{teacher_info['name']} {teacher_info['surname']}"
        location = teacher_info['location']
        year = teacher_info['year']

        text = (
            f"👨‍🏫 <b>O'qituvchi:</b> {full_name}\n"
            f"📍 <b>Filial:</b> {location}\n"
            f"📅 <b>Yil:</b> {year}\n\n"
            f"<b>🧾 Oylik ma'lumotlari:</b>\n\n"
        )

        for item in salary_list:
            debt = item['debt'] if item['debt'] is not None else 0
            text += (
                f"🗓 <b>{item['month']}</b>\n"
                f"💰 Umumiy oylik: <b>{item['total_salary']:,} so'm</b>\n"
                f"✅ Olingan: <b>{item['taken_money']:,} so'm</b>\n"
                f"❗ Qolgan: <b>{item['remaining_salary']:,} so'm</b>\n"
                f"💳 Qarz: <b>{debt:,} so'm</b>\n"
                f"{'━' * 25}\n"
            )

        await message.answer(text, parse_mode="HTML")
