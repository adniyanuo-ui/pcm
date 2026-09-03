# _*_coding:utf-8_*_
# __author: guo
import os
import sys

from celery import Celery
from kombu import Queue

project_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
sys.path.append(os.path.join(project_dir))

project_name = os.path.basename(project_dir)
# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', f'{project_name}.settings')

app = Celery(project_name)

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
# - namespace='CELERY' means all celery-related configuration keys
#   should have a `CELERY_` prefix.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
# app.autodiscover_tasks()

app.conf.update(
    task_queues={
        Queue("default", routing_key="default"),
    },
    task_routes={
        "llm.task.gen_prescription": {"queue": "default"},
    },
)
