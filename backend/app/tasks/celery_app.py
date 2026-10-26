"""
celery_app.py — Celery application instance configured with Redis as broker.
Includes graceful fallback if Celery or Redis is not installed/running locally.
"""

from __future__ import annotations

import logging
from app.core.config import settings

logger = logging.getLogger("aicte.celery")

try:
    from celery import Celery
    HAS_CELERY = True
except ImportError:
    Celery = None
    HAS_CELERY = False

if HAS_CELERY and Celery is not None:
    celery_app = Celery(
        "aicte_worker",
        broker=settings.REDIS_URL,
        backend=settings.REDIS_URL,
        include=[
            "app.tasks.ocr_tasks",
            "app.tasks.validation_tasks",
        ],
    )

    celery_app.conf.update(
        task_serializer="json",
        result_serializer="json",
        accept_content=["json"],
        timezone="Asia/Kolkata",
        enable_utc=True,
        task_track_started=True,
        task_acks_late=True,
        worker_prefetch_multiplier=1,
        task_routes={
            "app.tasks.ocr_tasks.*": {"queue": "ocr"},
            "app.tasks.validation_tasks.*": {"queue": "validation"},
        },
        beat_schedule={},
    )
else:
    class MockTask:
        def __init__(self, fn):
            self.fn = fn
            self.id = "local-sync-task"

        def delay(self, *args, **kwargs):
            try:
                result = self.fn(None, *args, **kwargs)
            except TypeError:
                result = self.fn(*args, **kwargs)
            class MockAsyncResult:
                id = "local-sync-task"
                def get(self, *a, **k):
                    return result
            return MockAsyncResult()

        def __call__(self, *args, **kwargs):
            return self.fn(*args, **kwargs)

    class MockCelery:
        def task(self, *args, **kwargs):
            def decorator(fn):
                return MockTask(fn)
            return decorator

    celery_app = MockCelery()
    logger.info("Celery library not found; initialized in-process asynchronous task runner fallback.")
