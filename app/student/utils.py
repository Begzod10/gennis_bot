from app.redis_client import redis_client
from app.models import Student, Parent, User
from app.db import SessionLocal
from typing import Dict, Optional
import json
import asyncio
import requests

timer_tasks: Dict[int, asyncio.Task] = {}
progress_messages: Dict[int, Dict[str, int]] = {}
QUESTION_TIME = 15


async def safe_get(url, **kwargs):
    def _get():
        return requests.get(url, timeout=kwargs.pop("timeout", 10), **kwargs)

    return await asyncio.to_thread(_get)


async def safe_post(url, json_payload=None, **kwargs):
    def _post():
        return requests.post(url, json=json_payload, timeout=kwargs.pop("timeout", 10), **kwargs)

    return await asyncio.to_thread(_post)


def get_platform_id(telegram_id: int) -> Optional[int]:
    session = SessionLocal()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            return user.platform_id
        return None
    finally:
        session.close()


def get_student(telegram_id):
    value = redis_client.get(f"parent:{telegram_id}:selected_student")
    print("value", value)
    with SessionLocal() as session:
        if not value:
            get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
            student = session.query(Student).filter(Student.user_id == get_user.id).first()
        else:
            data = json.loads(value)
            student_id = data["student_id"]
            parent_id = data["parent_id"]
            student = session.query(Student).filter(Student.id == student_id).first()
            parent = session.query(Parent).filter(Parent.id == parent_id).first()
            redis_client.set(f"parent:{telegram_id}:selected_student", json.dumps({
                "student_id": student.id,
                "parent_id": parent.id
            }))

    return student
