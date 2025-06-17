# tasks.py
from celery import Celery
import requests
from app.db import SessionLocal
from app.models import User, Student, Teacher
import os
from dotenv import load_dotenv
from .student.keyboards import student_basic_reply_keyboard
from .teacher.keyboards import teacher_basic_reply_keyboard
import app.keyboards as kb
from celery.schedules import crontab

load_dotenv()
celery = Celery('my_tasks', broker=os.getenv('CELERY_BROKER_URL'), backend=os.getenv('CELERY_RESULT_BACKEND'))

celery.conf.beat_schedule = {
    'send-balance-every-2-minutes': {
        'task': 'app.tasks.send_balance_to_users',
        'schedule': crontab(minute='*/1'),  # every 2 minutes
    },
}


@celery.task(name='app.tasks.process_login_task')
def process_login_task(telegram_id, username, password):
    import requests
    api = os.getenv('API')
    response = requests.post(f"{api}/api/login2", json={
        "username": username,
        "password": password
    })

    result = {
        "success": False,
        "user_type": None,
        "name": None,
        "surname": None,
        "error": "Login failed",
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
        session.commit()

        result["success"] = response.json()["success"]
        result["user_type"] = response.json()["type_user"]
        result["name"] = user.name
        result["surname"] = user.surname

        if user.user_type != result["user_type"]:
            user.user_type = result["user_type"]
            session.commit()

        if result["user_type"] == "student":
            student_data = user_data["student"]
            student = session.query(Student).filter(Student.user_id == user.id).first()
            if not student:
                student = Student(platform_id=student_data['id'], user_id=user.id)
                session.add(student)
            else:
                student.platform_id = student_data['id']
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

    return result


@celery.task(name='app.tasks.send_balance_to_users')
def send_balance_to_users():
    import os
    import requests
    import asyncio
    from aiogram import Bot
    from app.models import User, Student, Teacher
    from app.db import SessionLocal

    api = os.getenv('API')
    bot = Bot(token=os.getenv('TOKEN'))

    async def _send_all():
        async with bot.session:
            with SessionLocal() as session:
                users = session.query(User).all()
                for user in users:
                    if user.user_type == 'student':
                        student = session.query(Student).filter(Student.user_id == user.id).first()
                        platform_id = student.platform_id
                    elif user.user_type == 'teacher':
                        teacher = session.query(Teacher).filter(Teacher.user_id == user.id).first()
                        platform_id = teacher.platform_id
                    else:
                        continue

                    try:
                        response = requests.get(f'{api}/api/bot_student_balance/{platform_id}/{user.user_type}')
                        balance = response.json().get('balance')
                        text = f"📢 Sizning hisobingiz: {balance} so'm"
                        await bot.send_message(chat_id=user.telegram_id, text=text)
                    except Exception as e:
                        print(f"❌ Failed to send to {user.telegram_id}: {e}")

    # Run inside a new loop properly
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(_send_all())
    loop.close()
