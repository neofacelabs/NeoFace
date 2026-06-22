"""
NeoFace Verification Service
Orchestrates the face verification pipeline:
1. Detect face in query image
2. Run liveness detection (single-stage or full pipeline)
3. Generate ArcFace embedding
4. 1:N comparison against all enrolled users
5. Return match result with confidence + liveness + anti-spoof scores
6. Log authentication event

Pipeline mode is controlled by settings.USE_LIVENESS_PIPELINE (default True).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import VerificationLogger, logger
from app.repositories.auth_log_repository import AuthLogRepository
from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.verification import LivenessResult, VerificationResponse
from app.services.face_detector import FaceDetectorService
from app.services.face_embedding import FaceEmbeddingService
from app.services.liveness_service import LivenessCheckResult, LivenessService


class VerificationService:
    """
    Face verification business logic.
    Performs 1:N identity matching against all enrolled users.

    Liveness is run via the 6-stage pipeline (USE_LIVENESS_PIPELINE=True)
    which includes MiniFASNet passive anti-spoofing, or via the legacy
    single-stage MediaPipe path when the pipeline is disabled.
    """

    def __init__(
        self,
        db: AsyncSession,
        detector: FaceDetectorService,
        embedder: FaceEmbeddingService,
        liveness: LivenessService,
    ) -> None:
        self.db = db
        self.detector = detector
        self.embedder = embedder
        self.liveness = liveness
        self.user_repo = UserRepository(db)
        self.embedding_repo = EmbeddingRepository(db)
        self.log_repo = AuthLogRepository(db)

    # ── Public entry point ────────────────────────────────────────────────────

    async def verify(
        self,
        image_bytes: bytes,
        ip_address: str | None = None,
        user_agent: str | None = None,
        threshold: float | None = None,
        skip_liveness: bool = False,
        use_pipeline: bool | None = None,
    ) -> VerificationResponse:
        """
        Full face verification pipeline.

        Args:
            image_bytes:   Raw JPEG/PNG bytes from the HTTP request.
            ip_address:    Requester IP (written to audit log).
            user_agent:    HTTP User-Agent header (written to audit log).
            threshold:     Override for similarity threshold (defaults to settings).
            skip_liveness: Bypass liveness check — for testing only.
            use_pipeline:  Use full 6-stage pipeline (None = follow settings).

        Returns:
            VerificationResponse — always returned, never raises.
        """
        threshold = threshold or settings.SIMILARITY_THRESHOLD
        now = datetime.now(timezone.utc)

        # Decide which liveness path to take
        run_pipeline = (
            use_pipeline
            if use_pipeline is not None
            else settings.USE_LIVENESS_PIPELINE
        )

        VerificationLogger.verification_started(ip_address or "unknown")

        # ── Step 1: Detect face ───────────────────────────────────────────────
        detection_result, face = self.detector.detect_single(image_bytes)

        if not detection_result.success or face is None:
            reason = detection_result.error or "No face detected"
            await self._log_failure(reason=reason, ip_address=ip_address, user_agent=user_agent)
            VerificationLogger.verification_failed(reason, ip_address or "unknown")
            return self._build_failure_response(
                reason=reason,
                liveness=self._empty_liveness(),
                threshold=threshold, now=now,
            )

        # ── Step 2: Liveness detection ────────────────────────────────────────
        if skip_liveness:
            liveness_raw = self._bypass_liveness()
        elif run_pipeline:
            liveness_raw = self.liveness.analyze_with_pipeline(image_bytes)
        else:
            liveness_raw = self.liveness.analyze(image_bytes)

        liveness_schema = self._to_schema(liveness_raw)

        if not skip_liveness and not liveness_raw.is_live:
            reason = liveness_raw.failure_reason or "Liveness check failed"
            await self._log_failure(
                reason=reason,
                liveness_score=liveness_raw.score,
                ip_address=ip_address,
                user_agent=user_agent,
            )
            VerificationLogger.liveness_failed(ip_address or "unknown", liveness_raw.score)
            return self._build_failure_response(
                reason=reason,
                liveness=liveness_schema,
                threshold=threshold, now=now,
            )

        # ── Step 3: Generate query embedding ──────────────────────────────────
        try:
            query_embedding = self.embedder.get_embedding(face)
        except ValueError as exc:
            reason = f"Embedding generation failed: {exc}"
            await self._log_failure(
                reason=reason, liveness_score=liveness_raw.score,
                ip_address=ip_address, user_agent=user_agent,
            )
            return self._build_failure_response(
                reason=reason, liveness=liveness_schema,
                threshold=threshold, now=now,
            )

        # ── Step 4: 1:N similarity search ────────────────────────────────────
        neighbors = await self.embedding_repo.find_nearest_neighbors(query_embedding.tolist(), limit=1)

        if not neighbors:
            reason = "No enrolled users in the system"
            await self._log_failure(
                reason=reason, liveness_score=liveness_raw.score,
                ip_address=ip_address, user_agent=user_agent,
            )
            return self._build_failure_response(
                reason=reason, liveness=liveness_schema,
                threshold=threshold, now=now,
            )

        best_emb, raw_score = neighbors[0]

        # Map raw cosine similarity to calibrated percentage [0, 100]
        confidence_score = self.embedder.calibrate_similarity_score(raw_score)

        # ── Step 5: Handle no-match ───────────────────────────────────────────
        if raw_score < threshold:
            reason = "No matching face found"
            await self._log_failure(
                reason=reason,
                confidence_score=confidence_score,
                liveness_score=liveness_raw.score,
                ip_address=ip_address, user_agent=user_agent,
            )
            VerificationLogger.verification_completed(
                user_id="none", authenticated=False,
                confidence=confidence_score,
                liveness_score=liveness_raw.score,
                ip_address=ip_address or "unknown",
            )
            return self._build_failure_response(
                reason=reason, liveness=liveness_schema,
                threshold=threshold, confidence_score=confidence_score, now=now,
            )

        # ── Step 6: Validate matched user ─────────────────────────────────────
        matched_user_id = best_emb.user_id
        matched_user = await self.user_repo.get_by_id(matched_user_id)

        if not matched_user or not matched_user.is_active:
            reason = "Matched user account is inactive"
            await self._log_failure(
                reason=reason, user_id=matched_user_id,
                confidence_score=confidence_score, liveness_score=liveness_raw.score,
                ip_address=ip_address, user_agent=user_agent,
            )
            return self._build_failure_response(
                reason=reason, liveness=liveness_schema,
                threshold=threshold, confidence_score=confidence_score, now=now,
            )

        # ── Step 7: Write success audit log ───────────────────────────────────
        await self.log_repo.create(
            authentication_result=True,
            user_id=matched_user_id,
            confidence_score=confidence_score / 100,
            liveness_score=liveness_raw.score,
            ip_address=ip_address,
            user_agent=user_agent,
        )

        VerificationLogger.verification_completed(
            user_id=str(matched_user_id),
            authenticated=True,
            confidence=confidence_score,
            liveness_score=liveness_raw.score,
            ip_address=ip_address or "unknown",
        )

        return VerificationResponse(
            authenticated=True,
            user_id=matched_user_id,
            user_name=matched_user.name,
            confidence_score=confidence_score,
            liveness_score=liveness_raw.score,
            liveness_detail=liveness_schema,
            threshold_used=threshold,
            failure_reason=None,
            verified_at=now,
        )

    # ── Private helpers ───────────────────────────────────────────────────────

    async def _log_failure(
        self,
        reason: str,
        user_id: uuid.UUID | None = None,
        confidence_score: float | None = None,
        liveness_score: float | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> None:
        """Persist a failed authentication event to the audit trail."""
        try:
            await self.log_repo.create(
                authentication_result=False,
                user_id=user_id,
                confidence_score=(confidence_score / 100) if confidence_score else None,
                liveness_score=liveness_score,
                failure_reason=reason[:255],
                ip_address=ip_address,
                user_agent=user_agent,
            )
        except Exception as exc:
            logger.error("verification_service._log_failure: write failed", error=str(exc))

    @staticmethod
    def _to_schema(raw: LivenessCheckResult) -> LivenessResult:
        """Map internal LivenessCheckResult → Pydantic LivenessResult schema."""
        return LivenessResult(
            is_live=raw.is_live,
            score=raw.score,
            blink_detected=raw.blink_detected,
            head_turn_detected=raw.head_turn_detected,
            smile_detected=raw.smile_detected,
            checks_passed=raw.checks_passed,
            checks_total=raw.checks_total,
            anti_spoof_score=raw.anti_spoof_score,
            method=raw.method,
        )

    @staticmethod
    def _empty_liveness() -> LivenessResult:
        """Return a zero-filled LivenessResult for early-exit paths."""
        return LivenessResult(
            is_live=False, score=0.0,
            blink_detected=False, head_turn_detected=False, smile_detected=False,
            checks_passed=0, anti_spoof_score=0.0, method="none",
        )

    @staticmethod
    def _bypass_liveness() -> LivenessCheckResult:
        """Return a passing LivenessCheckResult for test bypass mode."""
        return LivenessCheckResult(
            is_live=True, score=100.0,
            blink_detected=True, head_turn_detected=True, smile_detected=True,
            ear_value=0.3, mouth_ratio=0.1, yaw_angle=20.0,
            checks_passed=3, anti_spoof_score=100.0, method="bypassed",
        )

    @staticmethod
    def _build_failure_response(
        reason: str,
        liveness: LivenessResult,
        threshold: float,
        confidence_score: float = 0.0,
        now: datetime | None = None,
    ) -> VerificationResponse:
        return VerificationResponse(
            authenticated=False,
            user_id=None, user_name=None,
            confidence_score=confidence_score,
            liveness_score=liveness.score,
            liveness_detail=liveness,
            threshold_used=threshold,
            failure_reason=reason,
            verified_at=now or datetime.now(timezone.utc),
        )
