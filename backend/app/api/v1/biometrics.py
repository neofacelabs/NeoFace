"""
NeoFace Biometrics API
Endpoints for enrolling and verifying iris and fingerprint biometrics.

POST /api/v1/biometrics/enroll/iris          — Enroll iris
POST /api/v1/biometrics/enroll/fingerprint   — Enroll fingerprint
POST /api/v1/biometrics/verify/iris          — 1:N iris identification
POST /api/v1/biometrics/verify/fingerprint   — 1:N fingerprint identification
GET  /api/v1/biometrics/status               — Enrollment status for current user
DELETE /api/v1/biometrics/iris               — Remove all iris data
DELETE /api/v1/biometrics/fingerprint        — Remove all fingerprint data
"""

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import TokenData, get_current_user
from app.repositories.biometric_repositories import IrisRepository, FingerprintRepository
from app.services.iris_service import IrisService
from app.services.fingerprint_service import FingerprintService, FingerprintTemplate as FPTemplate

router = APIRouter(prefix="/biometrics", tags=["Biometrics"])


# ── Iris Enrollment ────────────────────────────────────────────────────────────

@router.post(
    "/enroll/iris",
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a new iris for the authenticated user",
)
async def enroll_iris(
    eye_side: str = Form(default="right", description="left | right"),
    iris_image: UploadFile = File(..., description="Close-up eye image for iris enrollment"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Extract an IrisCode from the provided eye image and store it for the user.

    - Only 2 iris records per eye_side are allowed (left/right).
    - Images are NOT stored — only the 256-byte binary IrisCode is persisted.
    """
    if eye_side not in ("left", "right"):
        raise HTTPException(status_code=422, detail="eye_side must be 'left' or 'right'")

    image_bytes = await iris_image.read()
    service = IrisService.get_instance()
    iris_code = service.process_image(image_bytes)

    if iris_code is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract an IrisCode from the image. Ensure a clear, close-up iris photo is provided.",
        )

    if iris_code.usable_bits_ratio < 0.50:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Iris quality too low (usable_bits={iris_code.usable_bits_ratio:.2f}). Please retake the image with better lighting.",
        )

    repo = IrisRepository(db)
    count = await repo.count_by_user(current_user.user_uuid)
    if count >= 4:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Maximum iris enrollment limit reached (4 records). Delete existing records to re-enroll.",
        )

    record = await repo.create(
        user_id=current_user.user_uuid,
        iris_code=iris_code.code,
        iris_mask=iris_code.mask,
        eye_side=eye_side,
        quality_score=iris_code.quality_score,
        usable_bits_ratio=iris_code.usable_bits_ratio,
        source_image_bytes=image_bytes,
    )

    # Update user's is_iris_enrolled flag
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user.user_uuid)
    if user:
        user.is_iris_enrolled = True

    await db.commit()

    return {
        "enrolled": True,
        "iris_id": str(record.id),
        "eye_side": eye_side,
        "quality_score": iris_code.quality_score,
        "usable_bits_ratio": iris_code.usable_bits_ratio,
        "iris_code_sha256": iris_code.sha256,
        "message": f"Iris enrolled successfully for {eye_side} eye.",
    }


# ── Fingerprint Enrollment ─────────────────────────────────────────────────────

@router.post(
    "/enroll/fingerprint",
    status_code=status.HTTP_201_CREATED,
    summary="Enroll a fingerprint for the authenticated user",
)
async def enroll_fingerprint(
    finger_position: int = Form(default=2, description="ISO 19794-2 finger position code (1=right_thumb, 2=right_index...)"),
    impression_type: str = Form(default="live_scan", description="live_scan | rolled | latent"),
    fingerprint_image: UploadFile = File(..., description="Fingerprint scanner image"),
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Extract minutiae from the fingerprint image and store an ISO/IEC 19794-2 template.

    - Raw fingerprint images are NEVER stored.
    - Maximum 10 fingerprint records per user.
    """
    image_bytes = await fingerprint_image.read()
    service = FingerprintService.get_instance()
    template = service.extract_minutiae(image_bytes)

    if template is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Could not extract minutiae from the fingerprint image. Ensure a clear scanner image is provided.",
        )

    if template.minutiae_count < 10:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Too few minutiae detected ({template.minutiae_count}). Minimum 10 required. Please re-scan.",
        )

    repo = FingerprintRepository(db)
    count = await repo.count_by_user(current_user.user_uuid)
    if count >= 10:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Maximum fingerprint enrollment limit reached (10). Delete existing records to re-enroll.",
        )

    finger_labels = {1: "right_thumb", 2: "right_index", 3: "right_middle", 4: "right_ring", 5: "right_little",
                     6: "left_thumb", 7: "left_index", 8: "left_middle", 9: "left_ring", 10: "left_little"}
    label = finger_labels.get(finger_position, "unknown")

    record = await repo.create(
        user_id=current_user.user_uuid,
        template_data=template.to_bytes(),
        finger_position=finger_position,
        finger_position_label=label,
        minutiae_count=template.minutiae_count,
        quality_score=template.quality_score,
        impression_type=impression_type,
        source_image_bytes=image_bytes,
    )

    # Update user's is_fingerprint_enrolled flag
    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user.user_uuid)
    if user:
        user.is_fingerprint_enrolled = True

    await db.commit()

    return {
        "enrolled": True,
        "fingerprint_id": str(record.id),
        "finger_position": finger_position,
        "finger_label": label,
        "minutiae_count": template.minutiae_count,
        "quality_score": template.quality_score,
        "template_sha256": template.sha256,
        "message": f"Fingerprint enrolled for {label}.",
    }


# ── Iris Verification (1:N scan) ───────────────────────────────────────────────

@router.post(
    "/verify/iris",
    summary="Identify user from an iris image (1:N scan)",
)
async def verify_iris(
    iris_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Run 1:N iris identification against all enrolled IrisCodes.
    Returns the matched user's ID and Hamming Distance score.
    """
    image_bytes = await iris_image.read()
    service = IrisService.get_instance()
    iris_code = service.process_image(image_bytes)

    if iris_code is None:
        return {"matched": False, "failure_reason": "iris_extraction_failed", "hamming_distance": 1.0}

    repo = IrisRepository(db)
    enrolled = await repo.get_all()
    result = service.match(iris_code, enrolled)

    return {
        "matched": result.matched,
        "hamming_distance": result.hamming_distance,
        "match_score": result.match_score,
        "matched_user_id": result.matched_user_id,
        "threshold_used": result.threshold_used,
        "iris_quality": iris_code.quality_score,
        "usable_bits_ratio": iris_code.usable_bits_ratio,
    }


# ── Fingerprint Verification (1:N scan) ────────────────────────────────────────

@router.post(
    "/verify/fingerprint",
    summary="Identify user from a fingerprint image (1:N scan)",
)
async def verify_fingerprint(
    fingerprint_image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Run 1:N fingerprint identification against all enrolled minutiae templates.
    Returns the matched user's ID and match score.
    """
    image_bytes = await fingerprint_image.read()
    service = FingerprintService.get_instance()
    template = service.extract_minutiae(image_bytes)

    if template is None:
        return {"matched": False, "failure_reason": "minutiae_extraction_failed", "match_score": 0.0}

    repo = FingerprintRepository(db)
    enrolled = await repo.get_all()
    result = service.match(template, enrolled)

    return {
        "matched": result.matched,
        "match_score": result.match_score,
        "minutiae_pairs": result.minutiae_pairs,
        "matched_user_id": result.matched_user_id,
        "threshold_used": result.threshold_used,
        "minutiae_count": template.minutiae_count,
        "quality_score": template.quality_score,
    }


# ── Enrollment Status ──────────────────────────────────────────────────────────

@router.get(
    "/status",
    summary="Get biometric enrollment status for the authenticated user",
)
async def get_enrollment_status(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Returns which biometric modalities the user has enrolled."""
    iris_repo = IrisRepository(db)
    fp_repo = FingerprintRepository(db)

    iris_count = await iris_repo.count_by_user(current_user.user_uuid)
    fp_count = await fp_repo.count_by_user(current_user.user_uuid)

    from app.repositories.credential_repository import CredentialRepository
    webauthn_repo = CredentialRepository(db)
    webauthn_count = await webauthn_repo.count_active(current_user.user_uuid)

    from app.repositories.embedding_repository import EmbeddingRepository
    emb_repo = EmbeddingRepository(db)
    face_count = await emb_repo.count_by_user(current_user.user_uuid)

    fp_enrolled = fp_count > 0 or webauthn_count > 0

    return {
        "user_id": str(current_user.user_uuid),
        "face": {
            "enrolled": face_count > 0,
            "embedding_count": face_count,
        },
        "iris": {
            "enrolled": iris_count > 0,
            "record_count": iris_count,
        },
        "fingerprint": {
            "enrolled": fp_enrolled,
            "template_count": fp_count + webauthn_count,
        },
        "modalities_enrolled": sum([face_count > 0, fp_enrolled]),
        "max_security": face_count > 0 and fp_enrolled,
    }


# ── Delete Biometrics ──────────────────────────────────────────────────────────

@router.delete(
    "/face",
    status_code=status.HTTP_200_OK,
    summary="Remove all face embedding data for the authenticated user (self-service re-enrollment)",
)
async def delete_face(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Delete all ArcFace embeddings for the current user.
    After calling this, the user must re-enroll their face.
    Also resets the is_enrolled flag in Supabase.
    """
    from app.repositories.embedding_repository import EmbeddingRepository
    emb_repo = EmbeddingRepository(db)
    deleted = await emb_repo.delete_by_user(current_user.user_uuid)

    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user.user_uuid)
    if user:
        user.is_enrolled = False
    await db.commit()

    return {
        "deleted": True,
        "embeddings_deleted": deleted,
        "message": f"Deleted {deleted} face embedding(s). You may now re-enroll your face.",
    }


@router.delete(
    "/iris",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove all iris data for the authenticated user",
)
async def delete_iris(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all iris enrollment records for the current user (GDPR right-to-erasure)."""
    repo = IrisRepository(db)
    await repo.delete_by_user(current_user.user_uuid)

    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user.user_uuid)
    if user:
        user.is_iris_enrolled = False
    await db.commit()


@router.delete(
    "/fingerprint",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Remove all fingerprint data for the authenticated user",
)
async def delete_fingerprint(
    current_user: TokenData = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete all fingerprint enrollment records for the current user (GDPR right-to-erasure)."""
    repo = FingerprintRepository(db)
    await repo.delete_by_user(current_user.user_uuid)

    # Also deactivate all WebAuthn devices/fingerprints
    from app.models.biometric_credential import BiometricCredential
    from sqlalchemy import update
    await db.execute(
        update(BiometricCredential)
        .where(BiometricCredential.user_id == current_user.user_uuid)
        .values(is_active=False)
    )

    from app.repositories.user_repository import UserRepository
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(current_user.user_uuid)
    if user:
        user.is_fingerprint_enrolled = False
    await db.commit()
