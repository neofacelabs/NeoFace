"""
NeoFace Trust Engine — Liveness API (Modules 1 & 2)

POST /api/v1/liveness/check      — Passive liveness detection
POST /api/v1/liveness/challenge  — Generate active liveness challenge
POST /api/v1/liveness/verify     — Verify a challenge response frame
GET  /api/v1/liveness/challenge/{challenge_id} — Get active challenge state
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.models.trust_engine import LivenessLog
from app.services.active_liveness_service import ActiveLivenessService
from app.services.challenge_ai_service import ChallengeAIService
from app.services.passive_liveness_service import PassiveLivenessService
from app.services.face_detector import FaceDetectorService
from app.utils.dependencies import get_face_detector
from app.core.logging import logger

router = APIRouter(prefix="/liveness", tags=["Liveness"])

# Module-level service singletons
_passive_svc = PassiveLivenessService.get_instance()
_active_svc  = ActiveLivenessService.get_instance()
_challenge_svc: ChallengeAIService | None = None  # Initialized with Redis in lifespan


def _get_challenge_svc() -> ChallengeAIService:
    """Return the challenge AI service (initialized with Redis if available)."""
    global _challenge_svc
    if _challenge_svc is None:
        _challenge_svc = ChallengeAIService(redis_client=None)  # Redis injected in lifespan
    return _challenge_svc


# ── Response schemas ──────────────────────────────────────────────────────────

class PassiveLivenessResponse(BaseModel):
    liveness_score: float
    is_live: bool
    confidence: float
    attack_type: str
    method: str
    inference_ms: float
    model_available: bool
    v1_score: float | None = None
    v2_score: float | None = None


class ChallengeGenerateResponse(BaseModel):
    challenge_id: str
    challenge_type: str
    steps: list[str]
    descriptions: list[str]
    difficulty: str
    nonce: str
    expires_in_seconds: int = 60


class ChallengeVerifyResponse(BaseModel):
    challenge_completed: bool
    challenge_type: str
    steps_completed: list[str]
    steps_pending: list[str]
    confidence: float
    inference_ms: float
    failure_reason: str | None = None


# ─────────────────────────────────────────────────────────────────────────────
# PASSIVE LIVENESS CHECK
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/check",
    response_model=PassiveLivenessResponse,
    summary="Passive liveness detection (MiniFASNet anti-spoof)",
    status_code=status.HTTP_200_OK,
)
async def passive_liveness_check(
    request: Request,
    image: UploadFile = File(..., description="Face image for liveness check"),
    session_id: str | None = Form(default=None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PassiveLivenessResponse:
    """
    Passive liveness detection — no user action required.

    Submit a face image and receive a liveness verdict with attack type classification.
    Stores the result in liveness_logs for audit purposes.

    Returns:
        liveness_score: 0.0–1.0 probability of being live
        is_live: boolean decision
        confidence: 0–100 percentage
        attack_type: none | photo | screen | replay | mask | virtual_camera
    """
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Empty image file")

    # Detect face bounding box for cropping
    detector: FaceDetectorService = get_face_detector()
    detection, face = detector.detect_single(image_bytes)

    bbox = None
    if detection.success and face is not None:
        bbox = face.bbox

    result = _passive_svc.predict_from_bytes(image_bytes, bbox=bbox)

    # Persist to liveness_logs
    try:
        log = LivenessLog(
            user_id=current_user.user_uuid,
            liveness_score=result.liveness_score,
            is_live=result.is_live,
            confidence=result.confidence,
            anti_spoof_score=result.liveness_score * 100,
            attack_type=result.attack_type,
            check_type="passive",
            method=result.method,
            ip_address=request.client.host if request.client else None,
            session_id=session_id,
            extra={"v1_score": result.v1_score, "v2_score": result.v2_score},
        )
        db.add(log)
        await db.commit()
    except Exception as exc:
        logger.warning("liveness.check: log write failed", error=str(exc))

    return PassiveLivenessResponse(
        liveness_score=result.liveness_score,
        is_live=result.is_live,
        confidence=result.confidence,
        attack_type=result.attack_type,
        method=result.method,
        inference_ms=result.inference_ms,
        model_available=result.model_available,
        v1_score=result.v1_score,
        v2_score=result.v2_score,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVE LIVENESS — GENERATE CHALLENGE
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/challenge",
    response_model=ChallengeGenerateResponse,
    summary="Generate an active liveness challenge",
    status_code=status.HTTP_200_OK,
)
async def generate_challenge(
    request: Request,
    session_id: str | None = Form(default=None),
    last_challenge_type: str | None = Form(default=None, description="Previous challenge type (for anti-repeat)"),
    current_user: TokenData = Depends(get_current_user),
) -> ChallengeGenerateResponse:
    """
    Generate a randomized active liveness challenge.

    The challenge requires the user to perform specific facial actions (blink,
    smile, turn head, etc.) to prove they are physically present.
    Challenge sequences are never the same consecutively.

    Returns:
        challenge_id: Use this to verify frame responses
        steps: List of required actions in order
        descriptions: Human-readable instructions for the client UI
        nonce: Include in verification requests for anti-replay protection
    """
    challenge_svc = _get_challenge_svc()
    session_id = session_id or str(current_user.user_uuid)

    challenge = await challenge_svc.generate(
        session_id=session_id,
        user_id=str(current_user.user_uuid),
    )

    return ChallengeGenerateResponse(
        challenge_id=challenge.challenge_id,
        challenge_type=challenge.challenge_type,
        steps=challenge.steps,
        descriptions=challenge.descriptions,
        difficulty=challenge.difficulty,
        nonce=challenge.nonce,
        expires_in_seconds=60,
    )


# ─────────────────────────────────────────────────────────────────────────────
# ACTIVE LIVENESS — VERIFY CHALLENGE FRAME
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/verify",
    response_model=ChallengeVerifyResponse,
    summary="Verify an active liveness challenge frame",
    status_code=status.HTTP_200_OK,
)
async def verify_challenge_frame(
    request: Request,
    challenge_id: str = Form(...),
    nonce: str = Form(...),
    completed_steps: str = Form(default="[]", description="JSON array of already-completed steps"),
    image: UploadFile = File(..., description="Face frame to verify challenge action"),
    session_id: str | None = Form(default=None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ChallengeVerifyResponse:
    """
    Verify a single frame against an active liveness challenge.

    Submit frames continuously until challenge_completed=true.
    Track completed_steps between calls (returned in each response).

    The challenge is consumed (deleted) when all steps are verified.
    """
    import json

    challenge_svc = _get_challenge_svc()

    # Load and validate challenge
    challenge_data = await challenge_svc.get_challenge(challenge_id)
    if challenge_data is None:
        raise HTTPException(status_code=404, detail="Challenge not found or expired")

    # Parse completed steps
    try:
        steps_done: list[str] = json.loads(completed_steps)
    except (json.JSONDecodeError, ValueError):
        steps_done = []

    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Empty image file")

    result = _active_svc.verify_frame(image_bytes, challenge_data, steps_done)

    # If challenge fully completed, consume it (anti-replay)
    if result.challenge_completed:
        await challenge_svc.validate_and_consume(challenge_id, nonce)

        # Log the completed challenge
        try:
            log = LivenessLog(
                user_id=current_user.user_uuid,
                is_live=True,
                confidence=result.confidence,
                check_type="active",
                challenge_type=result.challenge_type,
                challenge_completed=True,
                ip_address=request.client.host if request.client else None,
                session_id=session_id or str(current_user.user_uuid),
            )
            db.add(log)
            await db.commit()
        except Exception as exc:
            logger.warning("liveness.verify: log write failed", error=str(exc))

    return ChallengeVerifyResponse(
        challenge_completed=result.challenge_completed,
        challenge_type=result.challenge_type,
        steps_completed=result.steps_completed,
        steps_pending=result.steps_pending,
        confidence=result.confidence,
        inference_ms=result.inference_ms,
        failure_reason=result.failure_reason,
    )
