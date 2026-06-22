"""
NeoFace Enrollment Service
Orchestrates the face enrollment pipeline:
1. Validate images (blur, resolution, face count)
2. Detect faces (InsightFace)
3. Generate ArcFace embeddings
4. Average embeddings from multiple images
5. Store embedding + user record in database
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import EnrollmentLogger, logger
from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.enrollment import (
    EnrollmentResponse,
    EnrollmentRequest,
    FaceQualityResult,
)
from app.services.face_detector import FaceDetectorService
from app.services.face_embedding import FaceEmbeddingService
from app.utils.storage import StorageService


class EnrollmentError(Exception):
    """Raised when enrollment cannot proceed."""
    pass


class EnrollmentService:
    """
    Face enrollment business logic.
    Injected into API route handlers via FastAPI dependency injection.
    """

    def __init__(
        self,
        db: AsyncSession,
        detector: FaceDetectorService,
        embedder: FaceEmbeddingService,
        storage: StorageService,
    ) -> None:
        self.db = db
        self.detector = detector
        self.embedder = embedder
        self.storage = storage
        self.user_repo = UserRepository(db)
        self.embedding_repo = EmbeddingRepository(db)

    async def enroll(
        self,
        request: EnrollmentRequest,
        image_files: list[bytes],
    ) -> EnrollmentResponse:
        """
        Full enrollment pipeline.

        Args:
            request: User metadata (name, email, phone)
            image_files: List of raw image bytes (1–5 images)

        Returns:
            EnrollmentResponse with user_id, status, confidence

        Raises:
            EnrollmentError: If enrollment cannot be completed
        """
        EnrollmentLogger.enrollment_started(request.email, len(image_files))

        # ── Step 1: Validate image count ──────────────────────────────────────
        if len(image_files) < settings.MIN_ENROLLMENT_IMAGES:
            raise EnrollmentError(
                f"Minimum {settings.MIN_ENROLLMENT_IMAGES} image(s) required, "
                f"got {len(image_files)}"
            )
        if len(image_files) > settings.MAX_ENROLLMENT_IMAGES:
            raise EnrollmentError(
                f"Maximum {settings.MAX_ENROLLMENT_IMAGES} images allowed, "
                f"got {len(image_files)}"
            )

        # ── Step 2: Detect faces and validate quality ─────────────────────────
        quality_results: list[FaceQualityResult] = []
        valid_faces = []

        for idx, img_bytes in enumerate(image_files):
            detection_result, face = self.detector.detect_single(img_bytes)

            if not detection_result.success or face is None:
                quality_results.append(
                    FaceQualityResult(
                        image_index=idx,
                        passed=False,
                        width=detection_result.image_width,
                        height=detection_result.image_height,
                        blur_score=detection_result.blur_score,
                        face_detected=False,
                        face_count=detection_result.face_count,
                        quality_score=0.0,
                        rejection_reason=detection_result.error,
                    )
                )
                logger.warning(
                    "Image rejected during enrollment",
                    index=idx,
                    reason=detection_result.error,
                )
                continue

            quality_results.append(
                FaceQualityResult(
                    image_index=idx,
                    passed=True,
                    width=detection_result.image_width,
                    height=detection_result.image_height,
                    blur_score=detection_result.blur_score,
                    face_detected=True,
                    face_count=1,
                    quality_score=face.quality_score,
                    rejection_reason=None,
                )
            )
            valid_faces.append((face, img_bytes, idx))

        if not valid_faces:
            EnrollmentLogger.enrollment_failed(request.email, "No valid face images")
            raise EnrollmentError(
                "No valid face images found. Ensure images are clear, "
                "well-lit, and contain exactly one face."
            )

        # ── Step 3: Generate ArcFace embeddings ───────────────────────────────
        embeddings = []
        for face, img_bytes, idx in valid_faces:
            try:
                embedding = self.embedder.get_embedding(face)
                embeddings.append(embedding)
            except ValueError as exc:
                logger.warning("Embedding generation failed", index=idx, error=str(exc))

        if not embeddings:
            raise EnrollmentError("Failed to generate face embeddings from any image")

        # ── Step 4: Average embeddings ────────────────────────────────────────
        avg_embedding = self.embedder.average_embeddings(embeddings)

        # Compute enrollment confidence from quality scores
        avg_quality = sum(f.quality_score for f in quality_results if f.passed) / len(
            [f for f in quality_results if f.passed]
        )

        # ── Step 5: Create or retrieve user ───────────────────────────────────
        existing_user = await self.user_repo.get_by_email(request.email)

        if existing_user and existing_user.is_enrolled:
            # Re-enrollment: delete old embeddings and re-enroll
            deleted = await self.embedding_repo.delete_by_user(existing_user.id)
            logger.info(
                "Re-enrollment: deleted old embeddings",
                user_id=str(existing_user.id),
                deleted_count=deleted,
            )
            user = existing_user
        elif existing_user:
            user = existing_user
        else:
            user = await self.user_repo.create_biometric_user(
                name=request.name,
                email=request.email,
                phone=request.phone,
            )

        # ── Step 6: Store images and embedding ────────────────────────────────
        # Store first valid image as reference
        image_path: str | None = None
        img_bytes_ref: bytes | None = None
        if valid_faces:
            _, img_bytes_ref, _ = valid_faces[0]
            image_path = await self.storage.save_face_image(
                user_id=str(user.id),
                image_bytes=img_bytes_ref,
            )

        await self.embedding_repo.create(
            user_id=user.id,
            embedding_vector=self.embedder.embedding_to_list(avg_embedding),
            quality_score=avg_quality,
            source_image_path=image_path,
            source_image_bytes=img_bytes_ref,
        )

        # Mark user as enrolled
        await self.user_repo.mark_enrolled(user.id)

        # Ensure a default bank account is linked to this user for biometric checkout authorization
        try:
            from app.repositories.biometric_repositories import BankAccountRepository
            bank_repo = BankAccountRepository(self.db)
            existing_banks = await bank_repo.get_by_user(user.id)
            if not existing_banks:
                await bank_repo.create(
                    user_id=user.id,
                    bank_name="NeoFace Bank",
                    account_type="checking",
                    account_mask="9999",
                    routing_mask="1234",
                    account_holder_name=user.name,
                    encrypted_token="mock_stripe_token_for_sandbox",
                    token_provider="stripe",
                    external_account_id=f"acc_{uuid.uuid4().hex[:12]}",
                    currency="USD",
                    is_default=True,
                )
                logger.info("Automatically linked default mock bank account during enrollment", user_id=str(user.id))
        except Exception as exc:
            logger.warning("Failed to auto-link bank account during enrollment", user_id=str(user.id), error=str(exc))

        EnrollmentLogger.enrollment_completed(str(user.id), avg_quality)

        return EnrollmentResponse(
            user_id=user.id,
            status="enrolled",
            message=f"Successfully enrolled with {len(valid_faces)} image(s)",
            confidence=round(avg_quality, 2),
            images_processed=len(valid_faces),
            quality_results=quality_results,
            enrolled_at=datetime.now(timezone.utc),
        )

    async def get_enrollment_status(self, user_id: uuid.UUID) -> dict:
        """Check enrollment status for a user."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            return {"found": False}

        count = await self.embedding_repo.count_by_user(user_id)
        latest = await self.embedding_repo.get_latest_by_user(user_id)

        return {
            "found": True,
            "user_id": user_id,
            "is_enrolled": user.is_enrolled,
            "enrollment_count": count,
            "last_enrolled_at": latest.created_at if latest else None,
        }
