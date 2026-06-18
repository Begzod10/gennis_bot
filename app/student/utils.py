from app.redis_client import redis_client
from app.models import Student, Parent, User
from app.db import SessionLocal
import json
import logging

logger = logging.getLogger(__name__)


def get_student(telegram_id):
    try:
        value = redis_client.get(f"parent:{telegram_id}:selected_student")
    except Exception as e:
        logger.error(f"Redis get error: {e}")
        value = None
    print("value", value)
    with SessionLocal() as session:
        if not value:
            get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
            if not get_user:
                return None
            student = session.query(Student).filter(Student.user_id == get_user.id).first()
        else:
            data = json.loads(value)
            student_id = data["student_id"]
            parent_id = data["parent_id"]
            student = session.query(Student).filter(Student.id == student_id).first()
            parent = session.query(Parent).filter(Parent.id == parent_id).first()
            try:
                redis_client.set(f"parent:{telegram_id}:selected_student", json.dumps({
                    "student_id": student.id,
                    "parent_id": parent.id
                }))
            except Exception as e:
                logger.error(f"Redis set error: {e}")

    return student
