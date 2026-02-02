"""
IOSP - Core Celery Tasks
System-level background tasks
"""
import logging
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone

logger = logging.getLogger(__name__)


@shared_task(name='apps.core.tasks.celery_health_check')
def celery_health_check():
    """
    Celery health check task.
    Runs every 5 minutes to verify worker is alive.
    """
    timestamp = timezone.now().isoformat()
    cache.set('celery_last_heartbeat', timestamp, timeout=600)
    logger.info(f"Celery health check: {timestamp}")
    return {'status': 'healthy', 'timestamp': timestamp}


@shared_task(name='apps.core.tasks.test_task')
def test_task(message: str = "Hello"):
    """
    Test task for verifying Celery setup.

    Usage:
        from apps.core.tasks import test_task
        result = test_task.delay("Test message")
        print(result.get())
    """
    logger.info(f"Test task executed with message: {message}")
    return {'status': 'success', 'message': message}
