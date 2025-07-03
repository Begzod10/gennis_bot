from app.redis_client import redis_client
from app.db import SessionLocal
import json
from app.models import Student, Parent, User, Teacher

from sqlalchemy.orm import joinedload


def get_user_data(telegram_id):
    value = redis_client.get(f"parent:{telegram_id}:selected_student")
    print("value", value)
    with SessionLocal() as session:
        get_user = session.query(User).filter(User.telegram_id == telegram_id).first()
        teacher = session.query(Teacher).filter(Teacher.user_id == get_user.id).first()
        if not value:
            student = session.query(Student).filter(Student.user_id == get_user.id).first()
            parent = None
        else:
            data = json.loads(value)
            student_id = data["student_id"]
            parent_id = data["parent_id"]
            student = session.query(Student).filter(Student.id == student_id).first()
            parent = session.query(Parent).options(joinedload(Parent.students)).filter(Parent.id == parent_id).first()
            redis_client.set(f"parent:{telegram_id}:selected_student", json.dumps({
                "student_id": student.id,
                "parent_id": parent.id
            }))
    return get_user, teacher, student, parent
