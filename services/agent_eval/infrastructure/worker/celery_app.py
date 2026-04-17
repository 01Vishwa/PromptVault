"""Celery application instance for the eval-core async worker."""
import os

from celery import Celery

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

app = Celery(
    "eval_worker",
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=["services.agent_eval.infrastructure.worker.tasks"],
)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    result_expires=3600,
    task_track_started=True,
    worker_prefetch_multiplier=1,   # One task at a time per worker process
    task_acks_late=True,            # Acknowledge only after task completes
)
