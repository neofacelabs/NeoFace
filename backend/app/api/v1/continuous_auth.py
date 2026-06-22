"""
NeoFace Trust Engine — Continuous Authentication API (Module 12)

POST /api/v1/continuous-auth/session/start   — Start a continuous auth session
POST /api/v1/continuous-auth/session/check   — Submit a check frame
POST /api/v1/continuous-auth/session/end     — Terminate a session
GET  /api/v1/continuous-auth/session/{token} — Get session status
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.core.logging import logger
from app.models.trust_engine import ContinuousSession
from app.services.continuous_auth_service import (
    ContinuousAuthService,
    DEFAULT_CHECK_INTERVAL_SECONDS,
)
from app.services.passive_liveness_service import PassiveLivenessService
from app.services.eye_tracking_service import EyeTrackingService
from app.services.device_trust_service import DeviceTrustService

router = APIRouter(prefix="/continuous-auth", tags=["Continuous Authentication"])

_cont_auth_svc = ContinuousAuthService()
_passive_svc   = PassiveLivenessService.get_instance()
_eye_svc       = EyeTrackingService.get_instance()
_device_svc    = DeviceTrustService()


# ── Response schemas ──────────────────────────────────────────────────────────

class SessionStartResponse(BaseModel):
    session_token: str
    status: str
    current_trust_score: float
    check_interval_seconds: int
    started_at: datetime


class SessionCheckResponse(BaseModel):
    session_token: str
    action: str           # continue | reauth_required | suspend | terminate
    trust_score: float
    check_score: float
    status: str
    evaluated_at: datetime
    next_check_in_seconds: int


class SessionStatusResponse(BaseModel):
    session_token: str
    status: str
    current_trust_score: float
    started_at: datetime
    last_verified_at: datetime | None
    reauth_count: int
    check_interval_seconds: int


# ─────────────────────────────────────────────────────────────────────────────
# START SESSION
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/session/start",
    response_model=SessionStartResponse,
    summary="Start a continuous authentication session",
    status_code=status.HTTP_201_CREATED,
)
async def start_session(
    request: Request,
    check_interval: int = Form(default=DEFAULT_CHECK_INTERVAL_SECONDS, ge=10, le=300),
    device_id: str | None = Form(default=None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStartResponse:
    """
    Start a continuous authentication session after successful login.

    The session will perform biometric checks every `check_interval` seconds.
    If the trust score drops below 70, re-authentication is triggered.
    If it drops below 30, the session is terminated immediately.

    Returns a session_token to use in subsequent check calls.
    """
    session_data = ContinuousAuthService.create_session(
        user_id=current_user.user_uuid,
        device_id=device_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
        check_interval=check_interval,
    )

    session = ContinuousSession(
        user_id=current_user.user_uuid,
        session_token=session_data["session_token"],
        status="active",
        current_trust_score=session_data["current_trust_score"],
        check_interval_seconds=check_interval,
        device_id=device_id,
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent"),
    )
    db.add(session)
    await db.commit()
    await db.refresh(session)

    logger.info(
        "continuous_auth.start",
        user_id=str(current_user.user_uuid),
        session_token=session.session_token[:16],
        interval=check_interval,
    )

    return SessionStartResponse(
        session_token=session.session_token,
        status=session.status,
        current_trust_score=session.current_trust_score,
        check_interval_seconds=session.check_interval_seconds,
        started_at=session.started_at,
    )


# ─────────────────────────────────────────────────────────────────────────────
# SUBMIT CHECK FRAME
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/session/check",
    response_model=SessionCheckResponse,
    summary="Submit a continuous authentication check frame",
    status_code=status.HTTP_200_OK,
)
async def submit_check(
    request: Request,
    session_token: str = Form(...),
    image: UploadFile | None = File(default=None, description="Face frame for presence + liveness check"),
    device_signals: str | None = Form(default=None, description="JSON device signals (optional)"),
    behavior_score: float | None = Form(default=None, ge=0, le=100),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionCheckResponse:
    """
    Submit a periodic check frame for continuous authentication.

    The client should call this every `check_interval_seconds` with the latest:
    - A face frame (webcam snapshot)
    - Optional device signals
    - Optional behavioral score from the client SDK

    The server evaluates liveness + eye tracking + device trust and updates
    the session trust score accordingly.

    **Action responses:**
    - `continue`         — All good, continue the session
    - `reauth_required`  — Trust dropped, show re-auth prompt
    - `suspend`          — Session suspended, block UI
    - `terminate`        — Session terminated, force logout
    """
    import json

    # Load session
    session_q = select(ContinuousSession).where(
        ContinuousSession.session_token == session_token,
        ContinuousSession.user_id == current_user.user_uuid,
    )
    result = await db.execute(session_q)
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    if session.status in ("terminated",):
        raise HTTPException(status_code=410, detail="Session has been terminated")

    # ── Biometric checks ──────────────────────────────────────────────────────
    check_results: dict[str, Any] = {}

    if image is not None:
        image_bytes = await image.read()
        if image_bytes:
            # Passive liveness (face presence)
            passive = _passive_svc.predict_from_bytes(image_bytes)
            check_results["face_present"] = passive.is_live
            check_results["face_confidence"] = passive.confidence

            # Eye tracking (frozen eye detection)
            eye = _eye_svc.analyze(image_bytes)
            check_results["eye_confidence"] = eye.eye_confidence
            check_results["is_frozen_eyes"] = eye.is_frozen
    else:
        # No image provided — apply score decay based on elapsed time
        from app.models.trust_engine import BehaviorEvent
        from sqlalchemy import func
        from datetime import timedelta

        interval = session.check_interval_seconds or 30
        since = datetime.now(timezone.utc) - timedelta(seconds=2 * interval)
        recent_typing_q = select(func.count(BehaviorEvent.id)).where(
            BehaviorEvent.user_id == session.user_id,
            BehaviorEvent.event_type == "keyboard",
            BehaviorEvent.created_at >= since
        )
        recent_typing_res = await db.execute(recent_typing_q)
        active_user_typing = recent_typing_res.scalar_one() > 0

        session_dict = {
            "current_trust_score": session.current_trust_score,
            "last_verified_at": session.last_verified_at.isoformat() if session.last_verified_at else None,
            "check_interval_seconds": session.check_interval_seconds,
        }
        decayed = ContinuousAuthService.apply_score_decay(session_dict, active_user_typing=active_user_typing)
        check_results["face_present"] = None  # Unknown — no frame submitted
        check_results["face_confidence"] = decayed.get("current_trust_score")

    # Device trust
    if device_signals:
        try:
            signals = json.loads(device_signals)
            device_result = _device_svc.assess(signals, request.headers.get("user-agent", ""))
            check_results["device_trust_score"] = float(device_result.device_trust_score)
        except Exception as exc:
            logger.debug("continuous_auth.check: device signals parse error", error=str(exc))

    # Behavioral score (from client SDK)
    if behavior_score is not None:
        check_results["behavior_score"] = float(behavior_score)

    # ── Evaluate ──────────────────────────────────────────────────────────────
    session_dict = {
        "user_id": str(session.user_id),
        "session_token": session.session_token,
        "current_trust_score": session.current_trust_score,
        "status": session.status,
        "reauth_count": session.reauth_count,
        "check_interval_seconds": session.check_interval_seconds,
        "last_verified_at": session.last_verified_at.isoformat() if session.last_verified_at else None,
    }

    evaluation = _cont_auth_svc.evaluate_check(session_dict, check_results)

    # ── Persist updated session ───────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    updated = evaluation["session"]
    session.current_trust_score = updated["current_trust_score"]
    session.status = updated["status"]
    session.last_verified_at = now
    if "reauth_count" in updated:
        session.reauth_count = updated["reauth_count"]
    if updated.get("terminated_at"):
        session.terminated_at = datetime.fromisoformat(updated["terminated_at"])
        session.termination_reason = updated.get("termination_reason")

    await db.commit()

    return SessionCheckResponse(
        session_token=session_token,
        action=evaluation["action"],
        trust_score=evaluation["trust_score"],
        check_score=evaluation["check_score"],
        status=updated["status"],
        evaluated_at=now,
        next_check_in_seconds=evaluation["next_check_in_seconds"],
    )


# ─────────────────────────────────────────────────────────────────────────────
# END SESSION
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/session/end",
    summary="Terminate a continuous authentication session",
    status_code=status.HTTP_200_OK,
)
async def end_session(
    session_token: str = Form(...),
    reason: str = Form(default="user_logout"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Explicitly terminate a continuous authentication session (e.g., on logout)."""
    session_q = select(ContinuousSession).where(
        ContinuousSession.session_token == session_token,
        ContinuousSession.user_id == current_user.user_uuid,
    )
    result = await db.execute(session_q)
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    now = datetime.now(timezone.utc)
    session.status = "terminated"
    session.terminated_at = now
    session.termination_reason = reason[:255]
    await db.commit()

    return {"terminated": True, "session_token": session_token, "reason": reason}


# ─────────────────────────────────────────────────────────────────────────────
# GET SESSION STATUS
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/session/{session_token}",
    response_model=SessionStatusResponse,
    summary="Get continuous auth session status",
)
async def get_session_status(
    session_token: str,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SessionStatusResponse:
    """Retrieve the current status and trust score of a continuous auth session."""
    session_q = select(ContinuousSession).where(
        ContinuousSession.session_token == session_token,
        ContinuousSession.user_id == current_user.user_uuid,
    )
    result = await db.execute(session_q)
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")

    return SessionStatusResponse(
        session_token=session.session_token,
        status=session.status,
        current_trust_score=session.current_trust_score,
        started_at=session.started_at,
        last_verified_at=session.last_verified_at,
        reauth_count=session.reauth_count,
        check_interval_seconds=session.check_interval_seconds,
    )
