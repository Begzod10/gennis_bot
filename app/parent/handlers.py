from aiogram import types
from aiogram import Dispatcher
from app.redis_client import redis_client
from aiogram import Router
from app.models import User, Parent, Student
from app.db import SessionLocal
from app.student.keyboards import student_basic_reply_keyboard_for_parent
import json

parent_router = Router()


@parent_router.message()
async def handle_student_selection(message: types.Message):
    telegram_id = message.from_user.id
    selected_label = message.text.strip()

    redis_key = f"parent:{telegram_id}:student_map"
    value = redis_client.hget(redis_key, selected_label)
    if value:
        data = json.loads(value)
        parent_id = data["parent_id"]
        student_id = data["student_id"]
        with SessionLocal() as session:
            parent = session.query(Parent).filter(Parent.id == parent_id).first()
            student = session.query(Student).filter(Student.id == student_id).first()
        redis_client.set(f"parent:{telegram_id}:selected_student", json.dumps({
            "student_id": student.id,
            "parent_id": parent.id
        }))
        await message.answer(f"✅Tanlangan o'quvchi: {student.name} {student.surname}",
                             reply_markup=student_basic_reply_keyboard_for_parent)
