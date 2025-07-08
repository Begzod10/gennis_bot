from aiogram.types import Message
from aiogram import F, Router
import app.keyboards as kb
from app.redis_client import redis_client
from aiogram.fsm.context import FSMContext

import requests

from app.student.keyboards import student_basic_reply_keyboard, student_basic_reply_keyboard_for_parent
from app.teacher.keyboards import teacher_basic_reply_keyboard
from app.parent.keyboards import generate_student_keyboard_for_parent
from app.states import MenuStates
from .utils import get_user_data
import os
from dotenv import load_dotenv
from app.teacher.handlers import selected_year, teacher_years_data
from app.student.handlers import user_years_data, user_months_data, datas, selected_student_year, selected_student_month

load_dotenv()
user_router = Router()


@user_router.message(F.text == "🚪 Chiqish")
async def exit(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.clear()
    user_years_data.pop(telegram_id, None)
    user_months_data.pop(telegram_id, None)
    datas.pop(telegram_id, None)
    selected_student_year.pop(telegram_id, None)
    selected_student_month.pop(telegram_id, None)
    selected_year.pop(telegram_id, None)
    teacher_years_data.pop(telegram_id, None)
    value = redis_client.get(f"parent:{telegram_id}:selected_student")
    if value:
        redis_client.delete(f"parent:{telegram_id}:selected_student")
    await message.answer("Siz tizimdan chiqdingiz!", reply_markup=kb.login_keyboard)


@user_router.message(F.text == "📚 Darslar ro‘yhati")
async def get_darslar_royxati(message: Message):
    api = os.getenv('API')
    telegram_user = message.from_user
    telegram_id = telegram_user.id
    get_user, teacher, student, parent = get_user_data(telegram_id)
    if get_user.user_type == 'parent' or get_user.user_type == 'student':
        platform_id = student.platform_id
    elif get_user.user_type == 'teacher':
        platform_id = teacher.platform_id
    else:
        platform_id = None
    response = requests.get(f'{api}/api/bot/users/time_table/{platform_id}/{get_user.user_type}')
    tables = response.json()['table_list']
    if not tables:
        await message.answer("⚠️ Jadval topilmadi.")
        return
    if get_user.user_type == 'parent':
        name = student.name
    elif get_user.user_type == 'student':
        name = student.name
    else:
        name = get_user.name

    text = f"📅 <b>{name}, sizning dars jadvalingiz:</b>\n\n"
    for table in tables:
        text += f"🔷 <b>{table['subject']} ({table['name']})</b>\n"
        text += f"👨‍🏫 O'qituvchi: {table['teacher']}\n"
        text += "🗓️ <b>Darslar:</b>\n"
        for lesson in table['lessons']:
            text += (
                f"• {lesson['day']} | {lesson['from']} - {lesson['to']} | "
                f"{lesson['room']}\n"
            )
        text += "━" * 15 + "\n"

    await message.answer(text, parse_mode="HTML")


@user_router.message(F.text == "👤 Mening hisobim")
async def get_balance(message: Message):
    api = os.getenv('API')
    telegram_user = message.from_user
    telegram_id = telegram_user.id
    get_user, teacher, student, parent = get_user_data(telegram_id)
    if get_user.user_type == 'parent' or get_user.user_type == 'student':
        platform_id = student.platform_id
    elif get_user.user_type == 'teacher':
        platform_id = teacher.platform_id
    else:
        platform_id = None
    response = requests.get(f'{api}/api/bot/users/balance/{platform_id}/{get_user.user_type}')
    balance = response.json()['balance']
    if get_user.user_type == 'student':
        await message.answer(f"✅ Sizning hisobingiz: {balance} so'm")
    elif get_user.user_type == 'parent':
        await message.answer(f"✅ {student.name}ning hisobi: {balance} so'm")
    else:
        await message.answer(f"✅ Oxirgi 2 oydagi hisobingiz: {balance} so'm")


@user_router.message(F.text == "⬅️ Ortga qaytish")
async def back(message: Message, state: FSMContext):
    telegram_user = message.from_user
    telegram_id = telegram_user.id
    current_state = await state.get_state()
    get_user, teacher, student, parent = get_user_data(telegram_id)
    reply = None
    if get_user.user_type == 'parent':
        if current_state == MenuStates.attendances:
            reply = student_basic_reply_keyboard_for_parent
            await state.set_state(MenuStates.menu)
        elif current_state == MenuStates.menu:
            reply = generate_student_keyboard_for_parent(parent, telegram_id)
    elif get_user.user_type == 'student':
        if current_state == MenuStates.attendances:
            reply = student_basic_reply_keyboard
    elif get_user.user_type == 'teacher':
        if current_state == MenuStates.salary:
            reply = teacher_basic_reply_keyboard

    await message.answer("✅ Ortga qaytildingiz.", reply_markup=reply)
