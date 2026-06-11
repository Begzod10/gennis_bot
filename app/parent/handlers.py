import json
import logging

from aiogram import types, Router
from app.redis_client import redis_client
from app.models import Parent, Student
from app.db import SessionLocal
from app.student.keyboards import student_basic_reply_keyboard_for_parent

logger = logging.getLogger(__name__)
parent_router = Router()


@parent_router.message()
async def handle_student_selection(message: types.Message):
    telegram_id = message.from_user.id
    selected_label = message.text.strip()
    redis_key = f"parent:{telegram_id}:student_map"

    if not redis_client.hexists(redis_key, selected_label):
        return

    value = redis_client.hget(redis_key, selected_label)
    if not value:
        return

    data = json.loads(value)
    parent_id = data["parent_id"]
    student_id = data["student_id"]

    with SessionLocal() as session:
        parent = session.query(Parent).filter(Parent.id == parent_id).first()
        student = session.query(Student).filter(Student.id == student_id).first()

        if not parent or not student:
            logger.warning(
                "Student or parent not found: student_id=%s parent_id=%s telegram_id=%s",
                student_id, parent_id, telegram_id
            )
            redis_client.delete(redis_key)
            await message.answer("❌ Ma'lumotlar topilmadi. Qayta kiring.")
            return

        redis_client.set(
            f"parent:{telegram_id}:selected_student",
            json.dumps({"student_id": student.id, "parent_id": parent.id}),
            ex=600
        )
        student_name = f"{student.name} {student.surname}"

    await message.answer(
        f"✅ Tanlangan o'quvchi: {student_name}",
        reply_markup=student_basic_reply_keyboard_for_parent
    )
