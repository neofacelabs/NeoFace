"""
NeoFace Enrollment Schemas
Pydantic v2 models for face enrollment request/response.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class EnrollmentRequest(BaseModel):
    """
    Enrollment request metadata.
    Images are supplied as multipart form fields — not in this body.
    """

    name: str = Field(..., min_length=2, max_length=255, examples=["Alice Johnson"])
    email: EmailStr = Field(..., examples=["alice@example.com"])
    phone: str | None = Field(
        default=None,
        pattern=r"^\+?[1-9]\d{1,14}$",
        examples=["+14155552671"],
    )


class FaceQualityResult(BaseModel):
    """Per-image quality assessment result."""

    image_index: int
    passed: bool
    width: int
    height: int
    blur_score: float
    face_detected: bool
    face_count: int
    quality_score: float
    rejection_reason: str | None = None


class EnrollmentResponse(BaseModel):
    """Response returned after successful enrollment."""

    model_config = ConfigDict(from_attributes=True)

    user_id: uuid.UUID
    status: str = "enrolled"
    message: str
    confidence: float = Field(..., ge=0.0, le=100.0)
    images_processed: int
    quality_results: list[FaceQualityResult]
    enrolled_at: datetime


class EnrollmentStatusResponse(BaseModel):
    """Check whether a user is enrolled."""

    user_id: uuid.UUID
    is_enrolled: bool
    enrollment_count: int  # number of embedding vectors stored
    last_enrolled_at: datetime | None
