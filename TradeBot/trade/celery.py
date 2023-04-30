import os
from celery import Celery
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'trade.settings')
app = Celery('trade')
app.config_from_object('django.conf:settings', namespace='CELERY')
CAR_BROKER_URL = 'redis://localhost:6379'
app.autodiscover_tasks()
@app.task
def print_hello():
    print('Hello from celery')

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')

