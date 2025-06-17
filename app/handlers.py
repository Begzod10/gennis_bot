import pprint

from aiogram.types import Message, KeyboardButton, CallbackQuery, ReplyKeyboardRemove
from aiogram.filters import CommandStart, Command
from aiogram import F, Router
import app.keyboards as kb
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from app.middlewares import TestMiddleware
import requests
from .student.keyboards import student_basic_reply_keyboard
from .teacher.keyboards import teacher_basic_reply_keyboard
from .models import User, Student, Teacher
from app.db import SessionLocal
from app.tasks import process_login_task

router = Router()
router.message.outer_middleware(TestMiddleware())


class Reg(StatesGroup):
    name = State()
    number = State()


class LoginStates(StatesGroup):
    waiting_for_username = State()
    waiting_for_password = State()


@router.message(CommandStart())
async def cmd_start(message: Message):
    await message.reply(
        "👋 Assalomu alaykum!\n\n"
        "🤖 <b>Gennis botiga xush kelibsiz!</b>\n\n"
        "Ushbu bot orqali siz quyidagi imkoniyatlardan foydalanishingiz mumkin:\n\n"
        "👨‍🏫 <b>O‘qituvchilar uchun:</b>\n"
        "   • 💳 Oylik ma'lumotlarini ko‘rish\n"
        "   • 📄 Har bir oy bo‘yicha tafsilotlarni olish\n\n"
        "👨‍🎓 <b>O‘quvchilar uchun:</b>\n"
        "   • 💳 To‘lovlar ro‘yxatini kuzatish\n"
        "   • 🎯 Test natijalari va\n"
        "   • 📝 Davomat statistikasini ko‘rish\n\n"
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

    # Start the Celery task
    task = process_login_task.delay(telegram_id, username, password)

    await message.answer("⏳ Tizimga kirish so‘rovi yuborildi...")

    # Wait up to 5 seconds for result (for demo purposes only)
    # try:
    result = task.get(timeout=5)  # ⚠️ avoid in production unless background
    if result['success']:
        reply_keyboard = student_basic_reply_keyboard if result[
                                                             'user_type'] == 'student' else teacher_basic_reply_keyboard
        emoji = {
            "student": "👨‍🎓",
            "teacher": "🧑‍🏫"
        }.get(result["user_type"], "👨‍💼")
        await message.answer(
            f"✅ {emoji} {result['name']} {result['surname']} ({result['user_type']})\n"
            f"Tizimga kirish muvaffaqiyatli amalga oshirildi", reply_markup=reply_keyboard
        )

    else:
        await message.answer("❌ Foydalanuvchi nomi yoki parol xato!", reply_markup=kb.login_keyboard)
    # except Exception:
    #     await message.answer("⚠️ So‘rov ishlovida xatolik yuz berdi. Keyinroq urinib ko‘ring.")

    await state.clear()


@router.message(F.text == "🚪 Chiqish")
async def exit(message: Message):
    await message.answer("Siz tizimdan chiqdingiz!", reply_markup=kb.login_keyboard)


@router.message(F.text == "📚 Darslar ro‘yhati")
async def get_darslar_royxati(message: Message):
    from run import api
    telegram_user = message.from_user
    telegram_id = telegram_user.id
    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        student = session.query(Student).filter(Student.user_id == get_user.id).first()
        teacher = session.query(Teacher).filter(Teacher.user_id == get_user.id).first()
        platform_id = student.platform_id if get_user.user_type == 'student' else teacher.platform_id
        response = requests.get(f'{api}/api/bot_student_time_table/{platform_id}/{get_user.user_type}')
        tables = response.json()['table_list']
        if not tables:
            await message.answer("⚠️ Jadval topilmadi.")
            return

        text = f"📅 <b>{telegram_user.first_name}, sizning dars jadvalingiz:</b>\n\n"
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
    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        student = session.query(Student).filter(Student.user_id == get_user.id).first()
        teacher = session.query(Teacher).filter(Teacher.user_id == get_user.id).first()
        platform_id = student.platform_id if get_user.user_type == 'student' else teacher.platform_id
        response = requests.get(f'{api}/api/bot_student_balance/{platform_id}/{get_user.user_type}')
        balance = response.json()['balance']
        await message.answer(f"✅ Sizning hisobingiz: {balance} so'm")


@router.message(F.text == "⬅️ Ortga qaytish")
async def back(message: Message):
    telegram_user = message.from_user
    telegram_id = telegram_user.id
    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
    reply = student_basic_reply_keyboard if get_user.user_type == 'student' else teacher_basic_reply_keyboard

    await message.answer("✅ Ortga qaytildingiz.", reply_markup=reply)
