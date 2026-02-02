"""
IOSP - Celery Configuration
Async task processing for document handling
"""
import os
from celery import Celery
from celery.schedules import crontab

# Set the default Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'iosp.settings')

# Create celery app
app = Celery('iosp')

# Load config from Django settings
app.config_from_object('django.conf:settings', namespace='CELERY')

# Celery Configuration
app.conf.update(
    # Broker settings
    broker_connection_retry_on_startup=True,
    broker_connection_retry=True,
    broker_connection_max_retries=10,

    # Task settings
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/Istanbul',
    enable_utc=True,

    # Task execution settings
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,

    # Result backend settings
    result_expires=3600,  # 1 hour

    # Task routing
    task_routes={
        'apps.documents.tasks.*': {'queue': 'documents'},
        'apps.rag.tasks.*': {'queue': 'rag'},
    },

    # Default queue
    task_default_queue='default',

    # Task time limits
    task_soft_time_limit=300,  # 5 minutes soft limit
    task_time_limit=600,  # 10 minutes hard limit

    # Retry settings
    task_default_retry_delay=60,  # 1 minute
    task_max_retries=3,
)

# Beat schedule (periodic tasks)
app.conf.beat_schedule = {
    # Clean up old failed documents every day at 3am
    'cleanup-failed-documents': {
        'task': 'apps.documents.tasks.cleanup_failed_documents',
        'schedule': crontab(hour=3, minute=0),
    },
    # Update document statistics every hour
    'update-document-stats': {
        'task': 'apps.documents.tasks.update_document_statistics',
        'schedule': crontab(minute=0),
    },
    # Health check every 5 minutes
    'celery-health-check': {
        'task': 'apps.core.tasks.celery_health_check',
        'schedule': crontab(minute='*/5'),
    },
}

# Auto-discover tasks from all installed apps
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Debug task for testing Celery."""
    print(f'Request: {self.request!r}')
