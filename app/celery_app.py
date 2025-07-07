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
    'send-balance-every-12-hours': {
        'task': 'app.tasks.send_balance_to_users',
        'schedule': crontab(minute=0, hour='0,12'),
    },
}

# celery.conf.beat_schedule = {
#     'send-balance-every-minute': {
#         'task': 'app.tasks.send_balance_to_users',
#         'schedule': crontab(),  # This runs the task every minute
#     },
# }

celery.conf.timezone = 'Asia/Tashkent'  # Optional but recommended
from app import tasks
