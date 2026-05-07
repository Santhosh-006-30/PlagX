import os
from celery import Celery
from app.config import settings

# Initialize Celery
celery_app = Celery(
    "plagx_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Optional configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600, # 1 hour max
)

# Auto-discover tasks from routers or services if needed
# For now, we will define the task in scan.py or a dedicated tasks module
celery_app.autodiscover_tasks(['app.api.routers'])
