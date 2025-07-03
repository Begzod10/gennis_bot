# app/keyboards.py
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.redis_client import redis_client
from app.models import Parent
import json

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import json


def generate_student_keyboard_for_parent(parent: Parent, telegram_id: int) -> ReplyKeyboardMarkup:
    buttons = []
    redis_key = f"parent:{telegram_id}:student_map"

    student_map = {}
    temp_row = []

    for student in parent.students:
        emoji = "🎓"
        full_name = f"{student.name or ''} {student.surname or ''}".strip()
        label = f"{emoji} {full_name or 'Student'}"

        # Store both parent_id and student_id as JSON
        student_map[label] = json.dumps({
            "parent_id": parent.id,
            "student_id": student.id
        })

        temp_row.append(KeyboardButton(text=label))

        # Once we collect 2 buttons, add them as a row
        if len(temp_row) == 2:
            buttons.append(temp_row)
            temp_row = []

    # Add the last row if only 1 button is left
    if temp_row:
        buttons.append(temp_row)

    # Add the "Exit" button in its own row
    buttons.append([KeyboardButton(text="🚪 Chiqish")])

    redis_client.hset(redis_key, mapping=student_map)
    redis_client.expire(redis_key, 600)  # Optional: expire after 10 minutes

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
