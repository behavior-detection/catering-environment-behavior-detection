import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "core.settings")

app = Celery("core")
app.config_from_object("django.conf:settings", namespace="CELERY")

# 自动发现tasks（会找到detection/tasks.py）
app.autodiscover_tasks()