import logging
import os

import requests
from aiogram import F, Router
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import User, Teacher
from app.states import MenuStates
from .keyboards import teacher_years_keyboard

load_dotenv()
logger = logging.getLogger(__name__)
teacher_router = Router()


@teacher_router.message(F.text == "💳 Oyliklar ro'yhati")
async def get_oyliklar_royxati(message: Message, state: FSMContext):
    api = os.getenv('API')
    telegram_id = message.from_user.id
    await state.set_state(MenuStates.salary)

    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not get_user:
            await message.answer("❌ Foydalanuvchi topilmadi.")
            return
        teacher = session.query(Teacher).filter(Teacher.user_id == get_user.id).first()
        if not teacher:
            await message.answer("❌ O'qituvchi ma'lumotlari topilmadi.")
            return
        teacher_platform_id = teacher.platform_id

    try:
        response = requests.get(
            f'{api}/api/bot/teachers/salary/years/{teacher_platform_id}',
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Failed to fetch salary years: %s", e)
        await message.answer("❌ Ma'lumotlarni olishda xatolik.")
        return

    years = data.get('years', [])
    await state.update_data(teacher_years=years, teacher_platform_id=teacher_platform_id)
    await message.answer("✅ Yilni tanlang:", reply_markup=await teacher_years_keyboard(years))


@teacher_router.message(StateFilter(MenuStates.salary))
async def handle_dynamic_year_selection(message: Message, state: FSMContext):
    api = os.getenv('API')
    telegram_id = message.from_user.id
    year = message.text.strip()

    data = await state.get_data()
    years = data.get('teacher_years', [])
    teacher_platform_id = data.get('teacher_platform_id')

    if year not in years:
        return

    if not teacher_platform_id:
        await message.answer("❌ O'qituvchi ma'lumotlari topilmadi.")
        return

    await message.answer(f"✅ Siz {year} yilni tanladingiz!")
    await state.update_data(selected_teacher_year=year)

    try:
        response = requests.get(
            f'{api}/api/bot/teachers/salary/{teacher_platform_id}/{year}',
            timeout=10
        )
        response.raise_for_status()
        data_resp = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Failed to fetch salary data: %s", e)
        await message.answer("❌ Ma'lumotlarni olishda xatolik.")
        return

    if not data_resp or not data_resp[0].get('salary_list'):
        await message.answer("⚠️ Bu yil uchun oylik ma'lumotlari topilmadi.")
        return

    teacher_info = data_resp[0]
    salary_list = teacher_info['salary_list']
    full_name = f"{teacher_info['name']} {teacher_info['surname']}"
    location = teacher_info['location']

    text = (
        f"👨‍🏫 <b>O'qituvchi:</b> {full_name}\n"
        f"📍 <b>Filial:</b> {location}\n"
        f"📅 <b>Yil:</b> {year}\n\n"
        f"<b>🧾 Oylik ma'lumotlari:</b>\n\n"
    )
    await message.answer(text, parse_mode="HTML")

    for item in salary_list:
        debt = item['debt'] if item['debt'] is not None else 0
        month = item['month']
        taken_money = item['taken_money'] if item['taken_money'] is not None else 0
        text = (
            f"🗓 <b>{month}</b>\n"
            f"💰 Umumiy oylik: <b>{item['total_salary']:,} so'm</b>\n"
            f"✅ Olingan: <b>{taken_money:,} so'm</b>\n"
            f"❗ Qolgan: <b>{item['remaining_salary']:,} so'm</b>\n"
            f"💳 Qarz: <b>{debt:,} so'm</b>\n"
            f"🖤 Black Salary: <b>{item['black_salary']:,} so'm</b>\n"
        )
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(
                    text="📄 Batafsil ko'rish",
                    callback_data=f"detail:{teacher_platform_id}:{item['id']}:{month}"
                )
            ]]
        )
        await message.answer(text, parse_mode="HTML", reply_markup=keyboard)


@teacher_router.callback_query(lambda c: c.data.startswith("detail:"))
async def handle_click(callback_query: CallbackQuery):
    api = os.getenv('API')
    _, teacher_id, salary_id, month = callback_query.data.split(":")
    await callback_query.answer()

    try:
        response = requests.get(
            f'{api}/api/bot/teachers/salary/details/{teacher_id}/{salary_id}',
            timeout=10
        )
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Failed to fetch salary details: %s", e)
        await callback_query.message.answer("❌ Ma'lumotlarni olishda xatolik.")
        return

    if not data or not isinstance(data, dict) or 'salary_list' not in data:
        await callback_query.message.answer("⚠️ Avans ma'lumotlari topilmadi.")
        return

    name = data.get("name", "Noma'lum")
    surname = data.get("surname", "")
    location = data.get("location", "❓")
    month = data.get("month", "❓")
    total_salary = data.get("total_salary", 0)
    taken_money = data.get("taken_money", 0)
    remaining_salary = data.get("remaining_salary", 0)
    black_salary = data.get("black_salary", 0)
    debt = data.get("debt") if data.get("debt") is not None else 0

    salary_list = data.get("salary_list", [])
    if not salary_list:
        await callback_query.message.answer("⚠️ Avans ma'lumotlari topilmadi.")
        return

    summary_text = (
        f"👨‍🏫 <b>O'qituvchi:</b> {name} {surname}\n"
        f"📍 <b>Filial:</b> {location}\n"
        f"📅 <b>Oy:</b> {month}\n\n"
        f"💰 <b>Umumiy oylik:</b> {total_salary:,} so'm\n"
        f"✅ <b>Olingan:</b> {taken_money:,} so'm\n"
        f"❗ <b>Qolgan:</b> {remaining_salary:,} so'm\n"
        f"💳 <b>Qarz:</b> {debt:,} so'm\n"
        f"🖤 Black Salary: <b>{black_salary:,} so'm</b>\n"
        f"{'━' * 25}\n"
        f"🧾 <b>Avanslar tafsiloti:</b>\n\n"
    )
    await callback_query.message.answer(summary_text, parse_mode="HTML")

    payment_text = ""
    for i, item in enumerate(salary_list, start=1):
        amount = item.get('amount', 0)
        date = item.get('date', '❓')
        payment_type = item.get('payment_type', '❓')
        reason = item.get('reason', '❓')
        emoji = "💳" if payment_type == "cash" else "🖱"
        payment_text += (
            f"🧾 <b>#{i}</b>\n"
            f"📅 <b>Sana:</b> {date}\n"
            f"💰 <b>Miqdor:</b> {amount:,} so'm\n"
            f"{emoji} <b>To'lov turi:</b> {payment_type}\n"
            f"📌 <b>Sabab:</b> {reason}\n"
            f"{'━' * 25}\n"
        )

    for i in range(0, len(payment_text), 4000):
        await callback_query.message.answer(payment_text[i:i + 4000], parse_mode="HTML")
