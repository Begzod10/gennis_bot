# app/celery_app.py

import os
from celery import Celery
from dotenv import load_dotenv
from celery.schedules import crontab

load_dotenv()

celery = Celery(
    'my_tasks',
    broker=os.getenv('CELERY_BROKER_URL'),
    backend=os.getenv('CELERY_RESULT_BACKEND')
)

celery.conf.beat_schedule = {
    'send-balance-daily-midnight': {
        'task': 'app.tasks.send_balance_to_users',
        'schedule': crontab(minute=0, hour=0),  # Runs at 00:00 every day
    },
}
# celery.conf.beat_schedule = {
#     'send-balance-daily-midnight': {
#         'task': 'app.tasks.send_balance_to_users',
#         'schedule': crontab(minute="*"),  # Runs at 00:00 every day
#     },
# }

celery.conf.timezone = 'Asia/Tashkent'  # Optional but recommended
from app import tasks
