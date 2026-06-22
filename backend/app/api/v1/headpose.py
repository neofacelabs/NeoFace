"""
NeoFace Trust Engine — Head Pose Estimation API (Module 4)

POST /api/v1/headpose — Estimate head pose (pitch, roll, yaw)
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.core.logging import logger
from app.models.trust_engine import HeadPoseLog
from app.services.headpose_service import HeadPoseService

router = APIRouter(prefix="/headpose", tags=["Head Pose"])

_headpose_svc = HeadPoseService.get_instance()


# ── Response schema ───────────────────────────────────────────────────────────

class HeadPoseResponse(BaseModel):
    pitch: float
    yaw: float
    roll: float
    is_frontal: bool
    is_extreme: bool
    method: str
    inference_ms: float


# ─────────────────────────────────────────────────────────────────────────────
# HEAD POSE ESTIMATION
# ─────────────────────────────────────────────────────────────────────────────

@router.post(
    "",
    response_model=HeadPoseResponse,
    summary="Estimate 3D head pose (pitch, roll, yaw)",
    status_code=status.HTTP_200_OK,
)
async def estimate_head_pose(
    request: Request,
    image: UploadFile = File(..., description="Face image for head pose estimation"),
    session_id: str | None = Form(default=None),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> HeadPoseResponse:
    """
    Estimate 3D head orientation using MediaPipe FaceMesh + OpenCV solvePnP.

    Used to verify realistic 3D movement as part of liveness verification
    and to detect static image attacks (no pose variation).

    Returns:
        pitch: Degrees — positive = looking up
        yaw:   Degrees — positive = facing right
        roll:  Degrees — positive = tilting clockwise
        is_frontal: True if within acceptable auth range (±30° yaw, ±25° pitch)
        is_extreme: True if pose exceeds ±45° on any axis (suspicious)
    """
    image_bytes = await image.read()
    if not image_bytes:
        raise HTTPException(status_code=422, detail="Empty image file")

    result = _headpose_svc.estimate(image_bytes)

    # Persist to headpose_logs
    try:
        log = HeadPoseLog(
            user_id=current_user.user_uuid,
            pitch=result.pitch,
            roll=result.roll,
            yaw=result.yaw,
            is_frontal=result.is_frontal,
            session_id=session_id,
            ip_address=request.client.host if request.client else None,
        )
        db.add(log)
        await db.commit()
    except Exception as exc:
        logger.warning("headpose.estimate: log write failed", error=str(exc))

    return HeadPoseResponse(
        pitch=result.pitch,
        yaw=result.yaw,
        roll=result.roll,
        is_frontal=result.is_frontal,
        is_extreme=result.is_extreme,
        method=result.method,
        inference_ms=result.inference_ms,
    )
