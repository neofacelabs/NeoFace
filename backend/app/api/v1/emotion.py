"""
NeoFace Trust Engine — Emotion Analysis API (Module 3)

POST /api/v1/emotion/analyze — Analyze facial emotion (secondary liveness signal)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.core.logging import logger
from app.models.trust_engine import EmotionLog
from app.services.emotion_service import EmotionService

from app.utils.dependencies import get_face_detector
from app.services.face_detector import FaceDetectorService

router = APIRouter(prefix="/emotion", tags=["Emotion"])

_emotion_svc = EmotionService.get_instance()


# ── Response schema ───────────────────────────────────────────────────────────

class EmotionAnalyzeResponse(BaseModel):
    emotion: str
    confidence: float
    all_scores: dict[str, float]
    method: str
    inference_ms: float
    model_available: bool


# ─────────────────────────────────────────────────────────────────────────────
# EMOTION ANALYSIS
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/analyze",
    response_model=EmotionAnalyzeResponse,
    summary="Analyze facial emotion (secondary liveness signal)",
    status_code=status.HTTP_200_OK,
)
async def analyze_emotion(
    request: Request,
    image: UploadFile = File(..., description="Face image for emotion analysis"),
    session_id: str | None = Form(default=None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    detector: FaceDetectorService = Depends(get_face_detector),
) -> EmotionAnalyzeResponse:
    """
    Detect the dominant facial emotion from an image.

    Used as a secondary liveness signal — real humans exhibit natural
    micro-expressions; spoofed faces tend to show static neutral emotions.

    NOT used for identity verification.

    Detects: happy | neutral | surprise | angry | sad | fear | disgust

    Returns:
        emotion: Dominant emotion label
        confidence: 0–100 classification confidence
        all_scores: Per-class probabilities (0–100)
    """
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Empty image file")

    bbox = None
    try:
        _, face = detector.detect_single(image_bytes)
        if face is not None:
            bbox = face.bbox
    except Exception as exc:
        logger.debug("emotion.analyze: face detection failed, using full image", error=str(exc))

    result = _emotion_svc.analyze_from_bytes(image_bytes, bbox=bbox)

    # Persist to emotion_logs
    try:
        log = EmotionLog(
            user_id=current_user.user_uuid,
            emotion=result.emotion,
            confidence=result.confidence,
            all_scores=result.all_scores,
            session_id=session_id,
            ip_address=request.client.host if request.client else None,
        )
        db.add(log)
        await db.commit()
    except Exception as exc:
        logger.warning("emotion.analyze: log write failed", error=str(exc))

    return EmotionAnalyzeResponse(
        emotion=result.emotion,
        confidence=result.confidence,
        all_scores=result.all_scores,
        method=result.method,
        inference_ms=result.inference_ms,
        model_available=result.model_available,
    )
