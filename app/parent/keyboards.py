# app/keyboards.py
import pprint

from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from app.redis_client import redis_client
from app.models import Parent, Student
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
import json

from dotenv import load_dotenv
import os
import requests

from app.db import SessionLocal

load_dotenv()


def generate_student_keyboard_for_parent(parent: Parent, telegram_id: int) -> ReplyKeyboardMarkup:
    api = os.getenv('API')
    response = requests.get(f'{api}/api/bot_parents_students/{parent.platform_id}')
    children = response.json()['children']
    buttons = []
    redis_key = f"parent:{telegram_id}:student_map"
    student_map = {}
    temp_row = []

    with SessionLocal() as session:
        # Bind parent to session to avoid DetachedInstanceError
        parent = session.merge(parent)
        parent.students = []

        if children:
            for child in children:
                student = session.query(Student).filter(Student.platform_id == child['id']).first()
                if not student:
                    student = Student(platform_id=child['id'], name=child['name'],
                                      surname=child['surname'])
                    session.add(student)
                else:
                    student.platform_id = child['id']
                    student.user_id = None
                    student.name = child['name']
                    student.surname = child['surname']
                if student not in parent.students:
                    parent.students.append(student)
            session.commit()

        for student in parent.students:
            emoji = "🎓"
            full_name = f"{student.name or ''} {student.surname or ''}".strip()
            label = f"{emoji} {full_name or 'Student'}"

            student_map[label] = json.dumps({
                "parent_id": parent.id,
                "student_id": student.id
            })

            temp_row.append(KeyboardButton(text=label))

            if len(temp_row) == 2:
                buttons.append(temp_row)
                temp_row = []

        if temp_row:
            buttons.append(temp_row)

    # Add the "Exit" button
    buttons.append([KeyboardButton(text="🚪 Chiqish")])

    redis_client.hset(redis_key, mapping=student_map)
    redis_client.expire(redis_key, 600)

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
