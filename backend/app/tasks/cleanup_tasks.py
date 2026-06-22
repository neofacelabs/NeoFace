"""
NeoFace Trust Engine — Cleanup Background Tasks
Periodic maintenance tasks for data hygiene and performance.

Tasks:
  cleanup_expired_challenges — Remove expired challenge tokens from DB
  archive_old_audit_logs     — Move old log records to cold storage / prune
  cleanup_terminated_sessions — Remove terminated sessions older than 30 days
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app

logger = get_task_logger(__name__)

# Retention periods
_CHALLENGE_LOG_RETENTION_DAYS    = 30
_LIVENESS_LOG_RETENTION_DAYS     = 90
_DEEPFAKE_LOG_RETENTION_DAYS     = 90
_EMOTION_LOG_RETENTION_DAYS      = 30
_HEADPOSE_LOG_RETENTION_DAYS     = 30
_DEVICE_LOG_RETENTION_DAYS       = 90
_BEHAVIOR_EVENT_RETENTION_DAYS   = 180
_TERMINATED_SESSION_RETENTION_DAYS = 30
_RISK_SCORE_RETENTION_DAYS       = 365


@celery_app.task(
    name="app.tasks.cleanup_tasks.cleanup_expired_challenges",
    bind=True,
    max_retries=2,
)
def cleanup_expired_challenges(self) -> dict:
    """Remove expired (unfulfilled) challenge log entries."""
    try:
        return asyncio.run(_cleanup_challenges_async())
    except Exception as exc:
        logger.error("cleanup_expired_challenges: error", exc_info=True)
        raise self.retry(exc=exc)


async def _cleanup_challenges_async() -> dict:
    from sqlalchemy import delete, func
    from app.core.database import AsyncSessionLocal
    from app.models.trust_engine import ChallengeLog

    cutoff = datetime.now(timezone.utc) - timedelta(days=_CHALLENGE_LOG_RETENTION_DAYS)

    async with AsyncSessionLocal() as db:
        stmt = delete(ChallengeLog).where(ChallengeLog.created_at < cutoff)
        result = await db.execute(stmt)
        await db.commit()
        deleted = result.rowcount

    logger.info("cleanup.challenges: purged old records", count=deleted, cutoff=cutoff.isoformat())
    return {"deleted_challenge_logs": deleted}


@celery_app.task(
    name="app.tasks.cleanup_tasks.archive_old_audit_logs",
    bind=True,
    max_retries=1,
)
def archive_old_audit_logs(self) -> dict:
    """
    Prune old Trust Engine log records beyond retention windows.
    Does NOT delete risk_scores or behavior_profiles (important audit data).
    """
    try:
        return asyncio.run(_archive_logs_async())
    except Exception as exc:
        logger.error("archive_old_audit_logs: error", exc_info=True)
        raise self.retry(exc=exc)


async def _archive_logs_async() -> dict:
    from sqlalchemy import delete
    from app.core.database import AsyncSessionLocal
    from app.models.trust_engine import (
        LivenessLog, EmotionLog, HeadPoseLog, DeepfakeLog,
        DeviceTrustLog, BehaviorEvent, ContinuousSession, ChallengeLog,
    )

    now = datetime.now(timezone.utc)
    totals: dict[str, int] = {}

    async with AsyncSessionLocal() as db:
        # Liveness logs
        cutoff = now - timedelta(days=_LIVENESS_LOG_RETENTION_DAYS)
        r = await db.execute(delete(LivenessLog).where(LivenessLog.created_at < cutoff))
        totals["liveness_logs"] = r.rowcount

        # Emotion logs
        cutoff = now - timedelta(days=_EMOTION_LOG_RETENTION_DAYS)
        r = await db.execute(delete(EmotionLog).where(EmotionLog.created_at < cutoff))
        totals["emotion_logs"] = r.rowcount

        # Head pose logs
        cutoff = now - timedelta(days=_HEADPOSE_LOG_RETENTION_DAYS)
        r = await db.execute(delete(HeadPoseLog).where(HeadPoseLog.created_at < cutoff))
        totals["headpose_logs"] = r.rowcount

        # Deepfake logs
        cutoff = now - timedelta(days=_DEEPFAKE_LOG_RETENTION_DAYS)
        r = await db.execute(delete(DeepfakeLog).where(DeepfakeLog.created_at < cutoff))
        totals["deepfake_logs"] = r.rowcount

        # Device trust logs
        cutoff = now - timedelta(days=_DEVICE_LOG_RETENTION_DAYS)
        r = await db.execute(delete(DeviceTrustLog).where(DeviceTrustLog.created_at < cutoff))
        totals["device_trust_logs"] = r.rowcount

        # Behavior events (keep profiles, prune raw events)
        cutoff = now - timedelta(days=_BEHAVIOR_EVENT_RETENTION_DAYS)
        r = await db.execute(delete(BehaviorEvent).where(BehaviorEvent.created_at < cutoff))
        totals["behavior_events"] = r.rowcount

        # Terminated continuous sessions
        cutoff = now - timedelta(days=_TERMINATED_SESSION_RETENTION_DAYS)
        r = await db.execute(
            delete(ContinuousSession).where(
                ContinuousSession.status == "terminated",
                ContinuousSession.terminated_at < cutoff,
            )
        )
        totals["continuous_sessions"] = r.rowcount

        await db.commit()

    logger.info("cleanup.archive: completed", totals=totals)
    return totals


@celery_app.task(
    name="app.tasks.cleanup_tasks.cleanup_terminated_sessions",
    bind=True,
)
def cleanup_terminated_sessions(self) -> dict:
    """Remove old terminated sessions (called separately if needed)."""
    try:
        return asyncio.run(_cleanup_sessions_async())
    except Exception as exc:
        raise self.retry(exc=exc)


async def _cleanup_sessions_async() -> dict:
    from sqlalchemy import delete
    from app.core.database import AsyncSessionLocal
    from app.models.trust_engine import ContinuousSession

    cutoff = datetime.now(timezone.utc) - timedelta(days=_TERMINATED_SESSION_RETENTION_DAYS)

    async with AsyncSessionLocal() as db:
        stmt = delete(ContinuousSession).where(
            ContinuousSession.status == "terminated",
            ContinuousSession.terminated_at < cutoff,
        )
        result = await db.execute(stmt)
        await db.commit()

    return {"deleted_sessions": result.rowcount}
