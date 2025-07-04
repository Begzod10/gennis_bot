import pprint

from aiogram.types import Message, KeyboardButton, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram import F, Router
import app.keyboards as kb
from app.redis_client import redis_client
from aiogram.fsm.context import FSMContext
from app.middlewares import TestMiddleware
import requests
from app.db import SessionLocal
from app.tasks import process_login_task
from app.models import Parent
from app.student.keyboards import student_basic_reply_keyboard, student_basic_reply_keyboard_for_parent
from app.teacher.keyboards import teacher_basic_reply_keyboard
from app.parent.keyboards import generate_student_keyboard_for_parent
from app.states import LoginStates, MenuStates
from .utils import get_user_data

router = Router()
router.message.outer_middleware(TestMiddleware())


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()

    await message.reply(
        "👋 Assalomu alaykum!\n\n"
        "🤖 <b>Gennis botiga xush kelibsiz!</b>\n\n"
        "Ushbu bot orqali siz quyidagi imkoniyatlardan foydalanishingiz mumkin:\n\n"
        "👨‍🏫 <b>O‘qituvchilar uchun:</b>\n"
        "   • 💳 Oylik ma'lumotlarini ko‘rish\n"
        "   • 📄 Har bir oy bo‘yicha tafsilotlarni olish\n\n"
        "👨‍🎓 <b>O‘quvchilar uchun:</b>\n"
        "   • 💳 To‘lovlar ro‘yxatini kuzatish\n"
        "   • 🎯 Test natijalari\n"
        "   • 📝 Davomat statistikasini ko‘rish\n\n"
        "👨‍👩‍👧‍👦 <b>Ota-onalar uchun:</b>\n"
        "   • 👨‍🎓 Farzandingizning test natijalari va davomatini ko‘rish\n"
        "   • 💳 To‘lov holatini nazorat qilish\n\n"
        "🔐 Botdan foydalanish uchun tizimga kiring.\n"
        "👇 Davom etish uchun quyidagi tugmani bosing:",
        parse_mode="HTML",
        reply_markup=kb.login_keyboard
    )


@router.message(F.text == "🔐 Tizimga kirish")
async def ask_username(message: Message, state: FSMContext):
    await message.answer(
        "👤 Iltimos, <b>foydalanuvchi nomingizni</b> kiriting:",
        parse_mode="HTML",
        reply_markup=ReplyKeyboardRemove()
    )
    await state.set_state(LoginStates.waiting_for_username)


@router.message(LoginStates.waiting_for_username)
async def get_username(message: Message, state: FSMContext):
    await state.update_data(username=message.text)
    await message.answer(
        "🔑 Endi <b>parolingizni</b> kiriting:",
        parse_mode="HTML"
    )
    await state.set_state(LoginStates.waiting_for_password)


@router.message(LoginStates.waiting_for_password)
async def get_password(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    user_data = await state.get_data()
    username = user_data['username']
    password = message.text
    print('test')
    task = process_login_task.delay(telegram_id, username, password)

    await message.answer("⏳ Tizimga kirish so‘rovi yuborildi...")
    result = task.get(timeout=5)  # ⚠️ avoid in production unless background
    if result['success']:
        if result['user_type'] == 'teacher':
            reply_keyboard = teacher_basic_reply_keyboard
        elif result['user_type'] == 'student':
            reply_keyboard = student_basic_reply_keyboard
        elif result['user_type'] == 'parent':
            get_parent = SessionLocal().query(Parent).filter(Parent.id == result['parent']).first()
            reply_keyboard = generate_student_keyboard_for_parent(get_parent, telegram_id)

            await state.set_state(MenuStates.menu)
        else:
            reply_keyboard = None
        emoji = {
            "student": "👨‍🎓",
            "teacher": "🧑‍🏫",
            "parent": "👨‍👩‍👦"
        }.get(result["user_type"], "👨‍💼")
        await message.answer(
            f"✅ {emoji} {result['name']} {result['surname']} ({result['user_type']})\n"
            f"Tizimga kirish muvaffaqiyatli amalga oshirildi", reply_markup=reply_keyboard
        )

    else:
        await message.answer("❌ Foydalanuvchi nomi yoki parol xato!", reply_markup=kb.login_keyboard)
        await state.clear()
        value = redis_client.get(f"parent:{telegram_id}:selected_student")
        if value:
            redis_client.delete(f"parent:{telegram_id}:selected_student")
    if result['user_type'] != 'parent':
        await state.clear()
        value = redis_client.get(f"parent:{telegram_id}:selected_student")
        if value:
            redis_client.delete(f"parent:{telegram_id}:selected_student")


@router.message(F.text == "🚪 Chiqish")
async def exit(message: Message, state: FSMContext):
    telegram_id = message.from_user.id
    await state.clear()
    value = redis_client.get(f"parent:{telegram_id}:selected_student")
    if value:
        redis_client.delete(f"parent:{telegram_id}:selected_student")
    await message.answer("Siz tizimdan chiqdingiz!", reply_markup=kb.login_keyboard)


@router.message(F.text == "📚 Darslar ro‘yhati")
async def get_darslar_royxati(message: Message):
    from run import api
    telegram_user = message.from_user
    telegram_id = telegram_user.id
    get_user, teacher, student, parent = get_user_data(telegram_id)
    if get_user.user_type == 'parent' or get_user.user_type == 'student':
        platform_id = student.platform_id
    elif get_user.user_type == 'teacher':
        platform_id = teacher.platform_id
    else:
        platform_id = None
    response = requests.get(f'{api}/api/bot_student_time_table/{platform_id}/{get_user.user_type}')
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


@router.message(F.text == "👤 Mening hisobim")
async def get_balance(message: Message):
    from run import api
    telegram_user = message.from_user
    telegram_id = telegram_user.id
    get_user, teacher, student, parent = get_user_data(telegram_id)
    if get_user.user_type == 'parent' or get_user.user_type == 'student':
        platform_id = student.platform_id
    elif get_user.user_type == 'teacher':
        platform_id = teacher.platform_id
    else:
        platform_id = None
    response = requests.get(f'{api}/api/bot_student_balance/{platform_id}/{get_user.user_type}')
    balance = response.json()['balance']
    if get_user.user_type == 'student':
        await message.answer(f"✅ Sizning hisobingiz: {balance} so'm")
    elif get_user.user_type == 'parent':
        await message.answer(f"✅ {student.name}ning hisobi: {balance} so'm")
    else:
        await message.answer(f"✅ Oxirgi 2 oydagi hisobingiz: {balance} so'm")


@router.message(F.text == "⬅️ Ortga qaytish")
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
