"""
NeoFace Trust Engine — Behavioral Biometrics API (Module 10)

POST /api/v1/behavior/events  — Submit behavioral events
POST /api/v1/behavior/score   — Get current behavior score
GET  /api/v1/behavior/profile — Get user behavioral profile
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.core.logging import logger
from app.models.trust_engine import BehaviorProfile as BehaviorProfileModel, BehaviorEvent as BehaviorEventModel
from app.services.behavioral_biometrics_service import (
    BehavioralBiometricsService,
    BehaviorEventData,
    BehaviorProfile,
)

router = APIRouter(prefix="/behavior", tags=["Behavioral Biometrics"])

_behavior_svc = BehavioralBiometricsService()


# ── Request/Response schemas ──────────────────────────────────────────────────

class BehaviorEventRequest(BaseModel):
    event_type: str = Field(..., description="mouse | keyboard | touch")
    metrics: dict[str, Any] = Field(..., description="Raw event metrics from client SDK")
    session_id: str | None = None


class BehaviorEventsBatchRequest(BaseModel):
    events: list[BehaviorEventRequest]
    session_id: str | None = None


class BehaviorScoreResponse(BaseModel):
    behavior_score: float
    is_anomalous: bool
    anomaly_score: float
    method: str
    component_scores: dict[str, float]
    risk_flags: list[str]


class BehaviorProfileResponse(BaseModel):
    user_id: str
    total_events: int
    is_baseline_established: bool
    avg_mouse_speed: float | None
    avg_typing_speed_wpm: float | None
    avg_swipe_velocity: float | None
    profile_version: int
    updated_at: datetime | None


# ─────────────────────────────────────────────────────────────────────────────
# SUBMIT BEHAVIOR EVENTS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/events",
    summary="Submit behavioral biometric events",
    status_code=status.HTTP_202_ACCEPTED,
)
async def submit_behavior_events(
    body: BehaviorEventsBatchRequest,
    request: Request,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Submit a batch of behavioral events for profile building and anomaly detection.

    Events are used to build the user's behavioral baseline over time.
    After 20 events, the Isolation Forest anomaly detector activates.

    **Mouse metrics:** speed_pxps, curvature, hesitation_rate
    **Keyboard metrics:** typing_speed_wpm, dwell_time_ms, flight_time_ms
    **Touch metrics:** swipe_velocity, touch_pressure, gesture_rhythm
    """
    if not body.events:
        raise HTTPException(status_code=422, detail="At least one event required")

    # Load or create profile
    profile_q = select(BehaviorProfileModel).where(
        BehaviorProfileModel.user_id == current_user.user_uuid
    )
    profile_result = await db.execute(profile_q)
    profile_row = profile_result.scalar_one_or_none()

    if profile_row is None:
        profile_row = BehaviorProfileModel(user_id=current_user.user_uuid)
        db.add(profile_row)
        await db.flush()

    # Map DB model to service dataclass
    service_profile = BehaviorProfile(
        user_id=str(current_user.user_uuid),
        total_events=profile_row.total_events,
        is_baseline_established=profile_row.is_baseline_established,
        avg_mouse_speed=profile_row.avg_mouse_speed,
        avg_mouse_curvature=profile_row.avg_mouse_curvature,
        avg_hesitation_rate=profile_row.avg_hesitation_rate,
        avg_typing_speed_wpm=profile_row.avg_typing_speed_wpm,
        avg_dwell_time_ms=profile_row.avg_dwell_time_ms,
        avg_flight_time_ms=profile_row.avg_flight_time_ms,
        avg_swipe_velocity=profile_row.avg_swipe_velocity,
        avg_touch_pressure=profile_row.avg_touch_pressure,
        avg_gesture_rhythm=profile_row.avg_gesture_rhythm,
        model_data=profile_row.model_data,
    )

    events = [BehaviorEventData(event_type=e.event_type, metrics=e.metrics) for e in body.events]

    # Score the new events (Phase 1 rule-based or Phase 2 IsolationForest)
    score_result = _behavior_svc.score(events, service_profile)

    # Update profile baseline
    prev_events = profile_row.total_events
    updated_profile = _behavior_svc.update_profile(service_profile, events)
    new_events = updated_profile.total_events

    # Trigger training when total_events cross a multiple of 200
    if new_events >= 200 and (prev_events // 200 < new_events // 200 or not profile_row.model_data):
        from app.tasks.behavior_training_task import train_behavior_model_async
        train_behavior_model_async.delay(str(current_user.user_uuid))

    # Persist updated profile
    profile_row.total_events = updated_profile.total_events
    profile_row.is_baseline_established = updated_profile.is_baseline_established
    profile_row.avg_mouse_speed = updated_profile.avg_mouse_speed
    profile_row.avg_mouse_curvature = updated_profile.avg_mouse_curvature
    profile_row.avg_hesitation_rate = updated_profile.avg_hesitation_rate
    profile_row.avg_typing_speed_wpm = updated_profile.avg_typing_speed_wpm
    profile_row.avg_dwell_time_ms = updated_profile.avg_dwell_time_ms
    profile_row.avg_flight_time_ms = updated_profile.avg_flight_time_ms
    profile_row.avg_swipe_velocity = updated_profile.avg_swipe_velocity
    profile_row.avg_touch_pressure = updated_profile.avg_touch_pressure
    profile_row.avg_gesture_rhythm = updated_profile.avg_gesture_rhythm

    # Persist events
    ip = request.client.host if request.client else None
    session_id = body.session_id

    for event in events:
        ev_row = BehaviorEventModel(
            profile_id=profile_row.id,
            user_id=current_user.user_uuid,
            event_type=event.event_type,
            metrics=event.metrics,
            is_anomalous=score_result.is_anomalous,
            anomaly_score=score_result.anomaly_score if score_result.anomaly_score != 0.0 else None,
            session_id=session_id,
            ip_address=ip,
        )
        db.add(ev_row)

    try:
        await db.commit()
    except Exception as exc:
        logger.warning("behavior.events: persist failed", error=str(exc))

    return {
        "accepted": len(events),
        "behavior_score": score_result.behavior_score,
        "is_anomalous": score_result.is_anomalous,
        "total_profile_events": updated_profile.total_events,
        "baseline_established": updated_profile.is_baseline_established,
    }


# ─────────────────────────────────────────────────────────────────────────────
# GET BEHAVIOR SCORE
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/score",
    response_model=BehaviorScoreResponse,
    summary="Score current behavioral events against user profile",
    status_code=status.HTTP_200_OK,
)
async def score_behavior(
    body: BehaviorEventsBatchRequest,
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BehaviorScoreResponse:
    """
    Compute a real-time behavioral trust score without persisting events.

    Useful for inline risk assessment during a transaction or session.
    """
    if not body.events:
        return BehaviorScoreResponse(
            behavior_score=75.0,
            is_anomalous=False,
            anomaly_score=0.0,
            method="no_data",
            component_scores={},
            risk_flags=[],
        )

    # Load profile (read-only for scoring)
    profile_q = select(BehaviorProfileModel).where(
        BehaviorProfileModel.user_id == current_user.user_uuid
    )
    profile_result = await db.execute(profile_q)
    profile_row = profile_result.scalar_one_or_none()

    service_profile = None
    if profile_row:
        service_profile = BehaviorProfile(
            user_id=str(current_user.user_uuid),
            total_events=profile_row.total_events,
            is_baseline_established=profile_row.is_baseline_established,
            avg_mouse_speed=profile_row.avg_mouse_speed,
            avg_typing_speed_wpm=profile_row.avg_typing_speed_wpm,
            avg_dwell_time_ms=profile_row.avg_dwell_time_ms,
            avg_swipe_velocity=profile_row.avg_swipe_velocity,
            model_data=profile_row.model_data,
        )

    events = [BehaviorEventData(event_type=e.event_type, metrics=e.metrics) for e in body.events]
    result = _behavior_svc.score(events, service_profile)

    return BehaviorScoreResponse(
        behavior_score=result.behavior_score,
        is_anomalous=result.is_anomalous,
        anomaly_score=result.anomaly_score,
        method=result.method,
        component_scores=result.component_scores,
        risk_flags=result.risk_flags,
    )


# ─────────────────────────────────────────────────────────────────────────────
# GET BEHAVIORAL PROFILE
# ─────────────────────────────────────────────────────────────────────────────

@router.get(
    "/profile",
    response_model=BehaviorProfileResponse,
    summary="Get user behavioral biometric profile",
)
async def get_behavior_profile(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> BehaviorProfileResponse:
    """Retrieve the current user's behavioral baseline profile."""
    profile_q = select(BehaviorProfileModel).where(
        BehaviorProfileModel.user_id == current_user.user_uuid
    )
    result = await db.execute(profile_q)
    profile = result.scalar_one_or_none()

    if profile is None:
        return BehaviorProfileResponse(
            user_id=str(current_user.user_uuid),
            total_events=0,
            is_baseline_established=False,
            avg_mouse_speed=None,
            avg_typing_speed_wpm=None,
            avg_swipe_velocity=None,
            profile_version=1,
            updated_at=None,
        )

    return BehaviorProfileResponse(
        user_id=str(profile.user_id),
        total_events=profile.total_events,
        is_baseline_established=profile.is_baseline_established,
        avg_mouse_speed=profile.avg_mouse_speed,
        avg_typing_speed_wpm=profile.avg_typing_speed_wpm,
        avg_swipe_velocity=profile.avg_swipe_velocity,
        profile_version=profile.profile_version,
        updated_at=profile.updated_at,
    )
