import json
import logging
import os

import requests
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from dotenv import load_dotenv

from app.db import SessionLocal
from app.models import Parent, Student
from app.redis_client import redis_client

load_dotenv()
logger = logging.getLogger(__name__)


def generate_student_keyboard_for_parent(parent: Parent, telegram_id: int) -> ReplyKeyboardMarkup:
    api = os.getenv('API')

    try:
        response = requests.get(
            f'{api}/api/bot/parents/students/{parent.platform_id}',
            timeout=10
        )
        response.raise_for_status()
        children = response.json().get('children', [])
    except (requests.RequestException, ValueError) as e:
        logger.error("Failed to fetch children for parent platform_id=%s: %s", parent.platform_id, e)
        children = []

    buttons = []
    redis_key = f"parent:{telegram_id}:student_map"
    student_map = {}
    temp_row = []

    with SessionLocal() as session:
        parent = session.merge(parent)

        if children:
            api_platform_ids = {child['id'] for child in children}
            existing_by_platform = {s.platform_id: s for s in parent.students}

            for child in children:
                if child['id'] in existing_by_platform:
                    student = existing_by_platform[child['id']]
                    student.name = child['name']
                    student.surname = child['surname']
                else:
                    student = session.query(Student).filter(
                        Student.platform_id == child['id']
                    ).first()
                    if not student:
                        student = Student(
                            platform_id=child['id'],
                            name=child['name'],
                            surname=child['surname']
                        )
                        session.add(student)
                    else:
                        student.name = child['name']
                        student.surname = child['surname']
                    parent.students.append(student)

            parent.students = [s for s in parent.students if s.platform_id in api_platform_ids]
            session.commit()

        for student in parent.students:
            full_name = f"{student.name or ''} {student.surname or ''}".strip()
            label = f"🎓 {full_name or 'Student'}"

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

    buttons.append([KeyboardButton(text="🚪 Chiqish")])

    if student_map:
        redis_client.hset(redis_key, mapping=student_map)
        redis_client.expire(redis_key, 600)

    return ReplyKeyboardMarkup(keyboard=buttons, resize_keyboard=True)
