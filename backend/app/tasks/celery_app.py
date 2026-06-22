"""
NeoFace Trust Engine — Celery Application
Background task worker configuration.

Queues:
  default          — General async tasks
  continuous_auth  — Periodic continuous authentication checks
  cleanup          — Stale session/log cleanup jobs

Beat Schedule (periodic tasks):
  continuous_auth_sweep  — Every 30s: run pending continuous auth checks
  cleanup_expired        — Every hour: purge expired sessions and old logs
"""

from __future__ import annotations

import os
# Force single-threaded execution for numerical libraries to prevent thread-safety segfaults on macOS/ARM
os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"
os.environ["OPENBLAS_NUM_THREADS"] = "1"
os.environ["VECLIB_MAXIMUM_THREADS"] = "1"
os.environ["NUMEXPR_NUM_THREADS"] = "1"

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

# ── Celery application ────────────────────────────────────────────────────────
celery_app = Celery(
    "neoface",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.continuous_auth_tasks",
        "app.tasks.cleanup_tasks",
        "app.tasks.behavior_training_task",
    ],
)

# ── Configuration ─────────────────────────────────────────────────────────────
celery_app.conf.update(
    # Serialization
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],

    # Timezone
    timezone="UTC",
    enable_utc=True,

    # Task routing
    task_routes={
        "app.tasks.continuous_auth_tasks.*": {"queue": "continuous_auth"},
        "app.tasks.cleanup_tasks.*": {"queue": "cleanup"},
        "app.tasks.behavior_training_task.*": {"queue": "default"},
    },

    # Result expiry
    result_expires=3600,           # 1 hour

    # Worker settings
    worker_prefetch_multiplier=4,
    worker_max_tasks_per_child=200,
    task_acks_late=True,           # Acknowledge after completion
    task_reject_on_worker_lost=True,

    # Retry settings
    task_max_retries=3,
    task_default_retry_delay=30,

    # Beat schedule
    beat_schedule={
        # Sweep continuous auth sessions every 30 seconds
        "continuous-auth-sweep": {
            "task": "app.tasks.continuous_auth_tasks.sweep_continuous_sessions",
            "schedule": 30.0,
            "options": {"queue": "continuous_auth"},
        },
        # Clean up expired challenge tokens every 10 minutes
        "cleanup-expired-challenges": {
            "task": "app.tasks.cleanup_tasks.cleanup_expired_challenges",
            "schedule": crontab(minute="*/10"),
            "options": {"queue": "cleanup"},
        },
        # Archive old liveness/deepfake logs every night at 2 AM
        "archive-old-logs": {
            "task": "app.tasks.cleanup_tasks.archive_old_audit_logs",
            "schedule": crontab(hour=2, minute=0),
            "options": {"queue": "cleanup"},
        },
    },
)

# ── Health check task ─────────────────────────────────────────────────────────
@celery_app.task(bind=True)
def debug_task(self):
    """Simple health check task — returns worker info."""
    return {
        "worker": self.request.hostname,
        "status": "healthy",
    }
