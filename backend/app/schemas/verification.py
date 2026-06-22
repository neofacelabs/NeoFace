"""
NeoFace Verification Schemas
Pydantic v2 models for face verification request/response.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class LivenessResult(BaseModel):
    """
    Detailed liveness detection breakdown returned to API consumers.
    Compatible with both legacy single-stage and multi-stage pipeline modes.
    """

    is_live: bool
    score: float = Field(..., ge=0.0, le=100.0, description="Composite liveness score (0–100)")
    blink_detected: bool
    head_turn_detected: bool
    smile_detected: bool
    checks_passed: int
    checks_total: int = 3

    # Anti-spoofing (populated when USE_LIVENESS_PIPELINE=True)
    anti_spoof_score: float = Field(
        default=0.0, ge=0.0, le=100.0,
        description="Passive anti-spoof confidence score (0–100). 0 when not run.",
    )
    method: str = Field(
        default="mediapipe_v1",
        description="Pipeline variant used: mediapipe_v1 | pipeline_v2+minifasnet | pipeline_v2+heuristic_fallback",
    )


class VerificationResponse(BaseModel):
    """
    Result of a face verification attempt.
    Returned for both successful and failed authentications.
    """

    model_config = ConfigDict(from_attributes=True)

    authenticated: bool
    user_id: uuid.UUID | None = None
    user_name: str | None = None
    confidence_score: float = Field(..., ge=0.0, le=100.0)
    liveness_score: float = Field(..., ge=0.0, le=100.0)
    liveness_detail: LivenessResult
    threshold_used: float
    failure_reason: str | None = None
    verified_at: datetime


class AuthLogResponse(BaseModel):
    """Single authentication log entry for dashboard."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID | None
    confidence_score: float | None
    liveness_score: float | None
    authentication_result: bool
    failure_reason: str | None
    ip_address: str | None
    timestamp: datetime


class AuthLogListResponse(BaseModel):
    """Paginated authentication log list."""

    total: int
    page: int
    page_size: int
    logs: list[AuthLogResponse]
