"""
NeoFace Enrollment API
Endpoints:
- POST /api/v1/enrollment          — Enroll a new user with face images
- GET  /api/v1/enrollment/{user_id} — Check enrollment status
- DELETE /api/v1/enrollment/{user_id} — Delete enrollment (admin only)
"""

import uuid

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status

from app.core.config import settings
from app.core.logging import logger
from app.core.security import TokenData, get_current_user_token, require_admin
from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.enrollment import EnrollmentRequest, EnrollmentResponse, EnrollmentStatusResponse
from app.services.face_detector import FaceDetectorService
from app.services.enrollment_service import EnrollmentError, EnrollmentService
from app.utils.dependencies import get_enrollment_service, get_face_detector

router = APIRouter(prefix="/enrollment", tags=["Face Enrollment"])

SUPPORTED_IMAGE_TYPES = {"image/jpeg", "image/png", "image/webp"}
MAX_IMAGE_SIZE_BYTES = int(settings.MAX_IMAGE_SIZE_MB * 1024 * 1024)


@router.post(
    "",
    response_model=EnrollmentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a new user with face images",
    description="""
    Upload 1–5 face images to enroll a new user.

    **Requirements:**
    - Images must be JPEG, PNG, or WebP
    - Maximum image size: 10MB each
    - Each image must contain exactly one face
    - Images must not be blurry
    - Minimum resolution: 112x112 pixels

    **Pipeline:**
    1. Validate image quality
    2. Detect face using InsightFace
    3. Generate 512-d ArcFace embedding
    4. Average embeddings from all valid images
    5. Store embedding and return user ID
    """,
    responses={
        201: {"description": "Successfully enrolled"},
        400: {"description": "Invalid images or face detection failed"},
        409: {"description": "Email already enrolled (re-enrollment will update)"},
        422: {"description": "Validation error"},
    },
)
async def enroll_user(
    name: str = Form(..., min_length=2, max_length=255, example="Alice Johnson"),
    email: str = Form(..., example="alice@example.com"),
    phone: str | None = Form(default=None, example="+14155552671"),
    images: list[UploadFile] = File(
        ...,
        description="1–5 face images (JPEG, PNG, or WebP)",
    ),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> EnrollmentResponse:
    """
    Enroll a user by uploading face images.
    Creates the user account if it doesn't exist, or re-enrolls if it does.
    """
    # ── Validate file count ────────────────────────────────────────────────
    if len(images) < settings.MIN_ENROLLMENT_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"At least {settings.MIN_ENROLLMENT_IMAGES} image(s) required",
        )
    if len(images) > settings.MAX_ENROLLMENT_IMAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {settings.MAX_ENROLLMENT_IMAGES} images allowed",
        )

    # ── Validate and read image files ─────────────────────────────────────
    image_bytes_list: list[bytes] = []

    for idx, upload in enumerate(images):
        # Content-type check
        if upload.content_type and upload.content_type not in SUPPORTED_IMAGE_TYPES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image {idx + 1}: unsupported type '{upload.content_type}'. "
                       f"Use JPEG, PNG, or WebP.",
            )

        # File size check
        image_data = await upload.read()
        if len(image_data) > MAX_IMAGE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image {idx + 1} exceeds maximum size of {settings.MAX_IMAGE_SIZE_MB}MB",
            )
        if len(image_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Image {idx + 1} is empty",
            )

        image_bytes_list.append(image_data)

    # ── Run enrollment pipeline ───────────────────────────────────────────
    request = EnrollmentRequest(name=name, email=email, phone=phone)

    try:
        result = await enrollment_service.enroll(request, image_bytes_list)
    except EnrollmentError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )

    return result


@router.post(
    "/validate-frame",
    status_code=status.HTTP_200_OK,
    summary="Validate a single face capture frame",
    description="Validate that a single captured face image contains exactly one clear face before saving it.",
)
async def validate_frame(
    file: UploadFile = File(...),
    detector: FaceDetectorService = Depends(get_face_detector),
) -> dict:
    """
    Validate a single face image frame captured during enrollment.
    """
    if file.content_type and file.content_type not in SUPPORTED_IMAGE_TYPES:
        return {
            "success": False,
            "error": f"Unsupported file type '{file.content_type}'. Use JPEG, PNG, or WebP.",
        }

    # File size check
    image_data = await file.read()
    if len(image_data) > MAX_IMAGE_SIZE_BYTES:
        return {
            "success": False,
            "error": f"Image exceeds maximum size of {settings.MAX_IMAGE_SIZE_MB}MB",
        }
    if len(image_data) == 0:
        return {
            "success": False,
            "error": "Image is empty",
        }

    detection_result, face = detector.detect_single(image_data)

    if not detection_result.success or face is None:
        return {
            "success": False,
            "error": detection_result.error or "No valid face image found.",
        }

    return {
        "success": True,
        "quality_score": face.quality_score,
    }


@router.get(
    "/{user_id}",
    response_model=EnrollmentStatusResponse,
    summary="Check enrollment status for a user",
)
async def get_enrollment_status(
    user_id: uuid.UUID,
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> EnrollmentStatusResponse:
    """Check whether a user is enrolled and how many embeddings are stored."""
    status_data = await enrollment_service.get_enrollment_status(user_id)

    if not status_data.get("found"):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    return EnrollmentStatusResponse(
        user_id=user_id,
        is_enrolled=status_data["is_enrolled"],
        enrollment_count=status_data["enrollment_count"],
        last_enrolled_at=status_data.get("last_enrolled_at"),
    )


@router.delete(
    "/{user_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a user's enrollment (admin only)",
)
async def delete_enrollment(
    user_id: uuid.UUID,
    token_data: TokenData = Depends(require_admin),
    enrollment_service: EnrollmentService = Depends(get_enrollment_service),
) -> dict:
    """
    Delete all face embeddings for a user and mark them as unenrolled.
    Requires admin role.
    """
    user_repo = UserRepository(enrollment_service.db)
    embedding_repo = EmbeddingRepository(enrollment_service.db)

    user = await user_repo.get_by_id(user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    deleted = await embedding_repo.delete_by_user(user_id)

    # Update enrollment flag
    from sqlalchemy import update
    from app.models.user import User
    from sqlalchemy import update
    await enrollment_service.db.execute(
        update(User)
        .where(User.id == user_id)
        .values(is_enrolled=False)
    )

    logger.info(
        "Enrollment deleted by admin",
        user_id=str(user_id),
        admin_id=token_data.user_id,
        deleted_count=deleted,
    )

    return {
        "message": f"Enrollment deleted for user {user_id}",
        "embeddings_deleted": deleted,
    }
