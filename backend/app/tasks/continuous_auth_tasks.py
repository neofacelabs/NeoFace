"""
NeoFace Trust Engine — Continuous Authentication Background Tasks
Runs every 30 seconds to sweep active sessions and apply score decay.

Workflow:
  1. Load all active/reauth_required sessions from DB
  2. For each session overdue for a check, apply score decay
  3. If score drops below threshold, update status and notify
  4. Persist changes back to DB

NOTE: This task applies passive score decay only.
      Actual biometric checks are triggered by client-submitted frames
      via POST /api/v1/continuous-auth/session/check.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone

from celery.utils.log import get_task_logger

from app.tasks.celery_app import celery_app
from app.services.continuous_auth_service import (
    ContinuousAuthService,
    REAUTH_THRESHOLD,
    SUSPEND_THRESHOLD,
)

logger = get_task_logger(__name__)

_cont_auth_svc = ContinuousAuthService()


@celery_app.task(
    name="app.tasks.continuous_auth_tasks.sweep_continuous_sessions",
    bind=True,
    max_retries=2,
    default_retry_delay=10,
)
def sweep_continuous_sessions(self) -> dict:
    """
    Sweep all active continuous authentication sessions.
    Apply score decay for sessions that have missed their check window.
    """
    try:
        result = asyncio.run(_sweep_sessions_async())
        return result
    except Exception as exc:
        logger.error("sweep_continuous_sessions: error", exc_info=True)
        raise self.retry(exc=exc)


async def _sweep_sessions_async() -> dict:
    """Async implementation of session sweep."""
    from sqlalchemy import select, update
    from app.core.database import AsyncSessionLocal
    from app.models.trust_engine import ContinuousSession

    updated_count = 0
    suspended_count = 0
    now = datetime.now(timezone.utc)

    async with AsyncSessionLocal() as db:
        # Load active sessions
        q = select(ContinuousSession).where(
            ContinuousSession.status.in_(["active", "reauth_required"])
        )
        result = await db.execute(q)
        sessions = result.scalars().all()

        for session in sessions:
            session_dict = {
                "current_trust_score": session.current_trust_score,
                "last_verified_at": session.last_verified_at.isoformat() if session.last_verified_at else None,
                "check_interval_seconds": session.check_interval_seconds,
            }

            # Check if overdue
            if not ContinuousAuthService.should_check_now(session_dict):
                continue

            from app.models.trust_engine import BehaviorEvent
            from sqlalchemy import func
            from datetime import timedelta

            interval = session.check_interval_seconds or 30
            since = now - timedelta(seconds=2 * interval)
            recent_typing_q = select(func.count(BehaviorEvent.id)).where(
                BehaviorEvent.user_id == session.user_id,
                BehaviorEvent.event_type == "keyboard",
                BehaviorEvent.created_at >= since
            )
            recent_typing_res = await db.execute(recent_typing_q)
            active_user_typing = recent_typing_res.scalar_one() > 0

            # Apply decay
            decayed = ContinuousAuthService.apply_score_decay(session_dict, active_user_typing=active_user_typing)
            new_score = decayed["current_trust_score"]

            if new_score == session.current_trust_score:
                continue

            session.current_trust_score = new_score
            updated_count += 1

            # Status transitions from decay
            if new_score < SUSPEND_THRESHOLD and session.status == "active":
                session.status = "suspended"
                suspended_count += 1
                logger.info(
                    "continuous_auth.sweep: session suspended (decay)",
                    session_id=str(session.id),
                    score=new_score,
                )
            elif new_score < REAUTH_THRESHOLD and session.status == "active":
                session.status = "reauth_required"
                logger.info(
                    "continuous_auth.sweep: reauth required (decay)",
                    session_id=str(session.id),
                    score=new_score,
                )

        if updated_count > 0:
            await db.commit()

    return {
        "sessions_checked": len(sessions) if "sessions" in dir() else 0,
        "sessions_updated": updated_count,
        "sessions_suspended": suspended_count,
        "swept_at": now.isoformat(),
    }
