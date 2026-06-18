import os
import asyncio
import logging
import requests

from app.db import SessionLocal
from app.models import User, Student, Teacher, Parent
from app.celery_app import celery

logger = logging.getLogger(__name__)


@celery.task(name='app.tasks.process_login_task')
def process_login_task(telegram_id, username, password):
    api = os.getenv('API')
    result = {
        "success": False,
        "user_type": None,
        "name": None,
        "surname": None,
        "error": "Login failed",
        "parent": None
    }

    try:
        # Force use of admin.gennis.uz as requested
        api_url = "https://admin.gennis.uz/api/base/login"
        response = requests.post(api_url, json={
            "username": username,
            "password": password
        }, timeout=10)
        response.raise_for_status()
        data = response.json()
    except (requests.RequestException, ValueError) as e:
        logger.error("Login API error for telegram_id=%s: %s", telegram_id, e)
        return result

    if 'user' not in data:
        return result

    parent_data = data.get('parent')
    user_data = data.get('user', {})

    if not user_data:
        logger.error("User data missing from API response for telegram_id=%s", telegram_id)
        return result

    with SessionLocal() as session:
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
            user.platform_id = user_data['id']
            try:
                requests.get(
                    f'https://admin.gennis.uz/api/bot/users/telegram_id/{user.platform_id}/{user.telegram_id}',
                    timeout=5
                )
            except requests.RequestException as e:
                logger.warning("Failed to update telegram_id on platform: %s", e)
        session.commit()

        result["success"] = data.get("success", False)
        result["user_type"] = data.get("type_user")
        result["name"] = user.name
        result["surname"] = user.surname

        if user.user_type != result["user_type"]:
            user.user_type = result["user_type"]
            session.commit()

        if result["user_type"] == "student":
            other_students = session.query(Student).filter(Student.user_id == user.id).all()
            for student in other_students:
                session.delete(student)
            session.commit()

            student_data = user_data.get("student", {})
            if not student_data:
                logger.error("Student data missing for student user_type, telegram_id=%s", telegram_id)
                # We continue as the User record is created, but student details are missing
                return result
            student = session.query(Student).filter(Student.platform_id == student_data['id']).first()
            if not student:
                student = Student(
                    platform_id=student_data['id'],
                    user_id=user.id,
                    name=user.name,
                    surname=user.surname
                )
                session.add(student)
            else:
                student.platform_id = student_data['id']
                student.user_id = user.id
            session.commit()

        elif result["user_type"] == "teacher":
            teacher_data = user_data.get("teacher", {})
            if not teacher_data:
                logger.error("Teacher data missing for teacher user_type, telegram_id=%s", telegram_id)
                return result
            teacher = session.query(Teacher).filter(Teacher.user_id == user.id).first()
            if not teacher:
                teacher = Teacher(platform_id=teacher_data['id'], user_id=user.id)
                session.add(teacher)
            else:
                teacher.platform_id = teacher_data['id']
            session.commit()
            parent_get = session.query(Parent).filter(Parent.user_id == user.id).first()
            if parent_get:
                session.delete(parent_get)
                session.commit()

        elif result["user_type"] == "parent":
            if not parent_data or 'parent_id' not in parent_data:
                logger.error("Parent data missing from API response for telegram_id=%s", telegram_id)
                return result

            parent_get = session.query(Parent).filter(Parent.user_id == user.id).first()
            if not parent_get:
                parent_get = Parent(platform_id=parent_data['parent_id'], user_id=user.id)
                session.add(parent_get)
            else:
                parent_get.platform_id = parent_data['parent_id']
            session.commit()
            result["parent"] = parent_get.id

    return result


def format_ball_history(ball_history):
    if not ball_history:
        return "\n⚠️ Ballar tarixi mavjud emas."

    history_lines = []
    for item in ball_history:
        subject = item.get("subject", "Noma'lum fan")
        average = item.get("average", 0)
        scored_days = item.get("scored_days", 0)
        history_lines.append(
            f"📚 {subject} — O'rtacha ball: {average}, Baholangan kun: {scored_days}"
        )

    return "\n" + "\n".join(history_lines)


@celery.task(name='app.tasks.send_balance_to_users')
def send_balance_to_users():
    from aiogram import Bot
    from aiogram.client.session.aiohttp import AiohttpSession
    from app.teacher.keyboards import teacher_basic_reply_keyboard
    from app.student.keyboards import student_basic_reply_keyboard
    from app.parent.keyboards import generate_student_keyboard_for_parent

    api = os.getenv('API')
    token = os.getenv('TOKEN')
    proxy = os.getenv('HTTPS_PROXY')

    async def _send_all():
        bot_session = AiohttpSession(proxy=proxy)
        bot = Bot(token=token, session=bot_session)
        try:
            with SessionLocal() as session:
                users = session.query(User).all()
                for user in users:
                    if user.user_type == 'student':
                        rel = session.query(Student).filter(Student.user_id == user.id).first()
                        platform_id = rel.platform_id if rel else None
                    elif user.user_type == 'teacher':
                        rel = session.query(Teacher).filter(Teacher.user_id == user.id).first()
                        platform_id = rel.platform_id if rel else None
                    elif user.user_type == 'parent':
                        rel = session.query(Parent).filter(Parent.user_id == user.id).first()
                        platform_id = rel.platform_id if rel else None
                    else:
                        continue

                    if not platform_id:
                        continue

                    try:
                        response = await asyncio.to_thread(
                            requests.get,
                            f'https://admin.gennis.uz/api/bot/users/balance/list/{platform_id}/{user.user_type}',
                            timeout=10
                        )
                        data = response.json()

                        if user.user_type in ("teacher", "student"):
                            keyboard = (
                                teacher_basic_reply_keyboard
                                if user.user_type == "teacher"
                                else student_basic_reply_keyboard
                            )
                            balance = data.get('balance')
                            ball_history = data.get('ball_history')
                            text = f"📢 Sizning hisobingiz: {balance} so'm"
                            text += format_ball_history(ball_history)
                            await bot.send_message(
                                chat_id=user.telegram_id, text=text, reply_markup=keyboard
                            )
                        else:
                            get_parent = session.query(Parent).filter(Parent.user_id == user.id).first()
                            reply_keyboard = generate_student_keyboard_for_parent(
                                get_parent, user.telegram_id
                            )
                            student_list = data.get('student_list', [])
                            for stud in student_list:
                                balance = stud.get('balance')
                                ball_history = stud.get('ball_history')
                                text = f"📢 {stud.get('name')}ning hisobi: {balance} so'm"
                                text += format_ball_history(ball_history)
                                await bot.send_message(
                                    chat_id=user.telegram_id, text=text, reply_markup=reply_keyboard
                                )

                    except Exception as e:
                        logger.error("Failed to send balance to %s: %s", user.telegram_id, e)
        finally:
            await bot.session.close()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(_send_all())
    finally:
        loop.close()
