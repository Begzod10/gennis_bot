from aiogram.types import Message, ReplyKeyboardRemove
from aiogram.filters import CommandStart
from aiogram import F, Router
import app.keyboards as kb
from app.redis_client import redis_client
from aiogram.fsm.context import FSMContext
from app.middlewares import TestMiddleware
from app.db import SessionLocal
from app.tasks import process_login_task
from app.models import Parent
from app.student.keyboards import student_basic_reply_keyboard
from app.teacher.keyboards import teacher_basic_reply_keyboard
from app.parent.keyboards import generate_student_keyboard_for_parent
from app.states import LoginStates, MenuStates
from dotenv import load_dotenv
from asyncio import sleep
load_dotenv()

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
    username = user_data["username"]
    password = message.text

    # 🔹 Send login task to Celery
    task = process_login_task.delay(telegram_id, username, password)

    await message.answer("⏳ Tizimga kirish so‘rovi yuborildi...")

    # 🔹 Poll Celery (max 10 seconds)
    result = None
    for _ in range(10):  # 10 × 1s = 10s wait
        if task.ready():
            result = task.result
            break
        await sleep(1)

    # 🔹 Handle timeout
    if not result:
        await message.answer("❌ Tizimdan javob olinmadi. Qayta urinib ko‘ring.")
        await state.clear()
        return

    # 🔹 Handle login success
    if result["success"]:
        if result["user_type"] == "teacher":
            reply_keyboard = teacher_basic_reply_keyboard

        elif result["user_type"] == "student":
            reply_keyboard = student_basic_reply_keyboard

        elif result["user_type"] == "parent":
            get_parent = SessionLocal().query(Parent).filter(Parent.id == result["parent"]).first()
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
            f"Tizimga kirish muvaffaqiyatli amalga oshirildi",
            reply_markup=reply_keyboard
        )

    # 🔹 Handle login failure
    else:
        await message.answer("❌ Foydalanuvchi nomi yoki parol xato!", reply_markup=kb.login_keyboard)
        await state.clear()

    # 🔹 Clear state for non-parent users
    if result["user_type"] != "parent":
        await state.clear()

    # 🔹 Reset Redis parent session if needed
    value = redis_client.get(f"parent:{telegram_id}:selected_student")
    if value:
        redis_client.delete(f"parent:{telegram_id}:selected_student")

