import json
import logging

from sqlalchemy.orm import joinedload

from app.db import SessionLocal
from app.models import Student, Parent, User, Teacher
from app.redis_client import redis_client

logger = logging.getLogger(__name__)


def get_user_data(telegram_id):
    try:
        value = redis_client.get(f"parent:{telegram_id}:selected_student")
    except Exception as e:
        logger.error(f"Redis get error: {e}")
        value = None
    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if not get_user:
            return None, None, None, None

        teacher = session.query(Teacher).filter(Teacher.user_id == get_user.id).first()

        if not value:
            student = session.query(Student).filter(Student.user_id == get_user.id).first()
            parent = None
        else:
            data = json.loads(value)
            student_id = data["student_id"]
            parent_id = data["parent_id"]
            student = session.query(Student).filter(Student.id == student_id).first()
            parent = session.query(Parent).options(
                joinedload(Parent.students)
            ).filter(Parent.id == parent_id).first()

            if not student or not parent:
                logger.warning(
                    "Stale Redis reference for telegram_id=%s: student_id=%s parent_id=%s",
                    telegram_id, student_id, parent_id
                )
                try:
                    redis_client.delete(f"parent:{telegram_id}:selected_student")
                except Exception as e:
                    logger.error(f"Redis delete error: {e}")
                student = None
                parent = None
            else:
                try:
                    redis_client.set(
                        f"parent:{telegram_id}:selected_student",
                        json.dumps({"student_id": student.id, "parent_id": parent.id}),
                        ex=600
                    )
                except Exception as e:
                    logger.error(f"Redis set error: {e}")

        session.expunge_all()

    return get_user, teacher, student, parent
