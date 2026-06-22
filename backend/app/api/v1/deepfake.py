"""
NeoFace Trust Engine — Deepfake Detection API (Module 8)

POST /api/v1/deepfake/check — Detect AI-generated or manipulated faces
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.core.logging import logger
from app.models.trust_engine import DeepfakeLog
from app.services.deepfake_service import DeepfakeService

from app.utils.dependencies import get_face_detector
from app.services.face_detector import FaceDetectorService

router = APIRouter(prefix="/deepfake", tags=["Deepfake Detection"])

_deepfake_svc = DeepfakeService.get_instance()


# ── Response schema ───────────────────────────────────────────────────────────

class DeepfakeCheckResponse(BaseModel):
    deepfake_probability: float
    is_deepfake: bool
    attack_category: str
    method: str
    classification_strength: float
    inference_ms: float
    model_available: bool
    efficientnet_score: float | None = None
    xceptionnet_score: float | None = None
    
    # Backward compatibility
    @property
    def confidence(self) -> float:
        """Deprecated: use classification_strength instead."""
        return self.classification_strength


# ─────────────────────────────────────────────────────────────────────────────
# DEEPFAKE DETECTION
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "/check",
    response_model=DeepfakeCheckResponse,
    summary="Detect AI-generated or deepfake faces",
    status_code=status.HTTP_200_OK,
)
async def deepfake_check(
    request: Request,
    image: UploadFile = File(..., description="Face image to analyze for deepfake artifacts"),
    session_id: str | None = Form(default=None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    detector: FaceDetectorService = Depends(get_face_detector),
) -> DeepfakeCheckResponse:
    """
    Analyze a face image for deepfake artifacts using EfficientNet-B4 / XceptionNet ensemble.

    Detects:
    - Face swap videos (e.g., FaceSwap, DeepFaceLab)
    - GAN-generated faces (StyleGAN, DALL-E, Midjourney)
    - Synthetic avatars and virtual faces
    - AI-manipulated facial features (FaceApp)

    The deepfake_score is INVERTED for the trust score engine:
    - deepfake_probability 0.04 → deepfake_score 96 (safe)
    - deepfake_probability 0.90 → deepfake_score 10 (dangerous)

    Returns:
        deepfake_probability: 0.0–1.0 (higher = more likely deepfake)
        is_deepfake: boolean decision at 0.5 threshold
        attack_category: face_swap | gan_face | synthetic_avatar | deepfake_video | none
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
        logger.debug("deepfake.check: face detection failed, using full image", error=str(exc))

    result = _deepfake_svc.detect(image_bytes, bbox=bbox)

    # Persist to deepfake_logs (store hash, not raw image)
    try:
        log = DeepfakeLog(
            user_id=current_user.user_uuid,
            deepfake_probability=result.deepfake_probability,
            is_deepfake=result.is_deepfake,
            model_used=result.method,
            attack_category=result.attack_category,
            inference_ms=result.inference_ms,
            image_hash=result.image_hash,
            session_id=session_id,
            ip_address=request.client.host if request.client else None,
            extra={
                "efficientnet_score": result.efficientnet_score,
                "xceptionnet_score": result.xceptionnet_score,
            },
        )
        db.add(log)
        await db.commit()
    except Exception as exc:
        logger.warning("deepfake.check: log write failed", error=str(exc))

    return DeepfakeCheckResponse(
        deepfake_probability=result.deepfake_probability,
        is_deepfake=result.is_deepfake,
        attack_category=result.attack_category,
        method=result.method,
        classification_strength=result.classification_strength,
        inference_ms=result.inference_ms,
        model_available=result.model_available,
        efficientnet_score=result.efficientnet_score,
        xceptionnet_score=result.xceptionnet_score,
    )
