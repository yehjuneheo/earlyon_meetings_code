import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'startup.settings')

app = Celery('startup')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()


app.conf.update(
    broker_transport_options={
        'region': 'us-east-2',
        'visibility_timeout': 3600,
        'polling_interval': 3,
        "is_secure": True,
        'queue_name_prefix': 'startup-',
    },
    result_backend=None,  # Typically, SQS is not used for results
    timezone='UTC',  # Set your desired timezone
    task_time_limit = 300,
    worker_max_memory_per_child = 100000,
    broker_connection_retry_on_startup = True
)

# Define the periodic tasks along with their schedule
app.conf.beat_schedule = {
    'send-meeting-reminders-every-30-minutes': {
        'task': 'myapp.tasks.send_meeting_reminders',
        'schedule': crontab(minute='*/30'),  # Executes every 30 minutes
    },
}