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
        "🤖 <b>Gennis botiga xush kelibsiz!</b>\n"
        "🔐 Botdan foydalanish uchun tizimga kirishingiz kerak.\n\n"
        "👇 Davom etish uchun quyidagi tugmani bosing!",
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
    from run import api
    telegram_user = message.from_user
    telegram_id = telegram_user.id

    user_data = await state.get_data()
    username = user_data['username']
    password = message.text

    response = requests.post(f'{api}/api/login2', json={
        'username': username,
        'password': password
    })
    if 'user' not in response.json():
        await message.answer("🚫 Foydalanuvchi nomi yoki parol xato!")
        return

    with SessionLocal() as session:
        platform_id = response.json()['user']['id']

        user = session.query(User).filter(
            User.telegram_id == telegram_id,
        ).first()

        if not user:
            user = User(telegram_id=telegram_id, platform_id=platform_id, name=response.json()['user']['name'],
                        surname=response.json()['user']['surname'], )
            session.add(user)
            session.commit()
        else:
            user.name = response.json()['user']['name']
            user.surname = response.json()['user']['surname']
            session.commit()
        if response.json()['type_user'] == 'student':
            student_data = response.json()['user']['student']

            user.user_type = 'student'
            session.commit()
            student = session.query(Student).filter(
                Student.user_id == user.id,
            ).first()

            if not student:
                student = Student(
                    platform_id=student_data['id'],
                    user_id=user.id
                )
                session.add(student)
                session.commit()
            student.platform_id = student_data['id']
            session.commit()
            reply_keyboard = student_basic_reply_keyboard
            emoji = "👨‍🎓"
        elif response.json()['type_user'] == 'teacher':
            user.user_type = 'teacher'
            session.commit()
            teacher_data = response.json()['user']['teacher']
            teacher = session.query(Teacher).filter(
                Teacher.user_id == user.id,
            ).first()

            if not teacher:
                teacher = Teacher(
                    platform_id=teacher_data['id'],
                    user_id=user.id
                )
                session.add(teacher)
                session.commit()
            teacher.platform_id = teacher_data['id']
            session.commit()
            reply_keyboard = teacher_basic_reply_keyboard
            emoji = "🧑‍🏫"
        else:
            reply_keyboard = None
            emoji = "👨‍💼"

        if response.json()['success']:
            await message.answer(
                f"{emoji} {response.json()['data']['name']} {response.json()['data']['surname']} ({response.json()['type_user']})"
                f"\nTizimga kirish muvaffaqiyatli amalga oshirildi", reply_markup=reply_keyboard)
        else:
            await message.reply("❌ Incorrect username or password.", reply_markup=kb.login_keyboard)

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
