import pprint

from app.db import SessionLocal
from app.models import User, Student, Teacher, Parent
import os
from app.celery_app import celery
import logging

logger = logging.getLogger(__name__)


@celery.task(name='app.tasks.process_login_task')
def process_login_task(telegram_id, username, password):
    logger.info('taskdan oldin')
    print('task ishladi')
    import requests
    api = os.getenv('API')
    response = requests.post(f"{api}/api/base/login", json={
        "username": username,
        "password": password
    })
    print(response)
    parent = response.json().get('parent') if 'parent' in response.json() else None
    result = {
        "success": False,
        "user_type": None,
        "name": None,
        "surname": None,
        "error": "Login failed",
        "parent": None
    }
    if 'user' not in response.json():
        return result

    with SessionLocal() as session:
        user_data = response.json()['user']

        user = session.query(User).filter(User.telegram_id == telegram_id).first()

        if not user:
            user = User(
                telegram_id=telegram_id,
                platform_id=user_data['id'],
                name=user_data['name'],
                surname=user_data['surname']
            )
            session.add(user)
        else:
            user.name = user_data['name']
            user.surname = user_data['surname']
            requests.get(f'{api}/api/bot/users/telegram_id/{user.platform_id}/{user.telegram_id}')
        session.commit()

        result["success"] = response.json()["success"]
        result["user_type"] = response.json()["type_user"]
        result["name"] = user.name
        result["surname"] = user.surname

        if user.user_type != result["user_type"]:
            user.user_type = result["user_type"]
            session.commit()

        if result["user_type"] == "student":
            other_students = session.query(Student).filter(Student.user_id == user.id).all()
            for student in other_students:
                student.user_id = None
                session.commit()
            student_data = user_data["student"]
            student = session.query(Student).filter(Student.platform_id == student_data['id']).first()
            if not student:
                student = Student(platform_id=student_data['id'], user_id=user.id, name=user.name, surname=user.surname)
                session.add(student)
            else:
                student.platform_id = student_data['id']
                student.user_id = user.id
            session.commit()

        elif result["user_type"] == "teacher":

            teacher_data = user_data["teacher"]
            teacher = session.query(Teacher).filter(Teacher.user_id == user.id).first()
            if not teacher:
                teacher = Teacher(platform_id=teacher_data['id'], user_id=user.id)
                session.add(teacher)
            else:
                teacher.platform_id = teacher_data['id']
            session.commit()
        elif result["user_type"] == "parent":

            parent_get = session.query(Parent).filter(Parent.user_id == user.id).first()
            if not parent_get:
                parent_get = Parent(platform_id=parent['parent_id'], user_id=user.id)
                session.add(parent_get)
            else:
                parent_get.platform_id = parent['parent_id']

            result["parent"] = parent_get.id
            session.commit()
    return result


def format_ball_history(ball_history):
    """Format ball_history list into readable text."""
    if not ball_history:
        return "\n⚠️ Ballar tarixi mavjud emas."

    history_lines = []
    for item in ball_history:
        subject = item.get("subject", "Noma'lum fan")
        average = item.get("average", 0)
        scored_days = item.get("scored_days", 0)
        history_lines.append(f"📚 {subject} — O'rtacha ball: {average}, Baholangan kun: {scored_days}")

    return "\n" + "\n".join(history_lines)


@celery.task(name='app.tasks.send_balance_to_users')
def send_balance_to_users():
    import os
    import requests
    import asyncio
    from aiogram import Bot
    from app.models import User, Student, Teacher, Parent
    from app.db import SessionLocal
    import pprint

    api = os.getenv('API')
    bot = Bot(token=os.getenv('TOKEN'))

    async def _send_all():
        async with bot.session:
            with SessionLocal() as session:
                users = session.query(User).all()
                for user in users:
                    if user.user_type == 'student':
                        student = session.query(Student).filter(Student.user_id == user.id).first()
                        platform_id = student.platform_id if student else None
                    elif user.user_type == 'teacher':
                        teacher = session.query(Teacher).filter(Teacher.user_id == user.id).first()
                        platform_id = teacher.platform_id if teacher else None
                    elif user.user_type == 'parent':
                        parent = session.query(Parent).filter(Parent.user_id == user.id).first()
                        platform_id = parent.platform_id if parent else None
                    else:
                        continue

                    try:
                        if platform_id:
                            response = requests.get(f'{api}/api/bot/users/balance/list/{platform_id}/{user.user_type}')
                            data = response.json()

                            if user.user_type in ("teacher", "student"):
                                balance = data.get('balance')
                                ball_history = data.get('ball_history')
                                text = f"📢 Sizning hisobingiz: {balance} so'm"
                                text += format_ball_history(ball_history)
                                await bot.send_message(chat_id=user.telegram_id, text=text)
                            else:  # parent
                                student_list = data.get('student_list', [])
                                for student in student_list:
                                    balance = student.get('balance')
                                    ball_history = student.get('ball_history')
                                    text = f"📢 {student.get('name')}ning hisobi: {balance} so'm"
                                    text += format_ball_history(ball_history)

                                    await bot.send_message(chat_id=user.telegram_id, text=text)

                    except Exception as e:
                        print(f"❌ Failed to send to {user.telegram_id}: {e}")

    # Run inside a new loop properly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_send_all())
    loop.close()
