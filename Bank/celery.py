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
    'loan-payment-due-mail': {
        'task': 'bank.tasks.loan_payment_due',
        'schedule': crontab(hour=6, minute=46)
    },
    'loan_paid':{
        'task': 'bank.tasks.loan_paid',
        'schedule': crontab(hour=6, minute=46)
    }
}