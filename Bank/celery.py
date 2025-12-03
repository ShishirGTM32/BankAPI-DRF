import os
from celery import Celery
from celery.schedules import crontab
from datetime import timedelta

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Bank.settings')

app = Celery('Bank')

app.config_from_object('django.conf:settings', namespace='CELERY')

app.autodiscover_tasks()

@app.task(bind=True, ignore_result=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

app.conf.beat_schedule = {
    'send-report-every-midnight': {
        'task': 'project.tasks.send_report',
        'schedule': crontab(hour=0, minute=0),  # every midnight
    },
    'cleanup-every-30-minutes': {
        'task': 'project.tasks.cleanup',
        'schedule': timedelta(minutes=30),
    },
}