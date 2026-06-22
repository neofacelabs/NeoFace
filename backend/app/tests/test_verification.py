"""
NeoFace Verification Tests
Tests for face verification pipeline and API endpoints.
"""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.auth_log_repository import AuthLogRepository
from app.repositories.embedding_repository import EmbeddingRepository
from app.services.face_detector import FaceDetectorService
from app.services.face_embedding import FaceEmbeddingService
from app.services.liveness_service import LivenessService
from app.services.verification_service import VerificationService
from app.tests.conftest import (
    make_fake_detected_face,
    make_fake_detection_result,
    make_fake_embedding,
    make_test_image_bytes,
)


class TestVerificationService:
    """Unit tests for VerificationService business logic."""

    @pytest_asyncio.fixture
    async def verification_service_with_enrolled_user(
        self, db_session: AsyncSession, enrolled_user
    ):
        """Create VerificationService with a known enrolled user."""
        user, embedding = enrolled_user

        detector = MagicMock(spec=FaceDetectorService)
        detector.detect_single.return_value = (
            make_fake_detection_result(success=True),
            make_fake_detected_face(seed=99),  # Same seed as enrolled embedding
        )
        detector._initialized = True

        embedder = FaceEmbeddingService()  # Use real embedder for similarity math

        liveness = MagicMock(spec=LivenessService)
        from app.services.liveness_service import LivenessCheckResult
        result = LivenessCheckResult(
            is_live=True,
            score=85.0,
            blink_detected=True,
            head_turn_detected=True,
            smile_detected=True,
            ear_value=0.25,
            mouth_ratio=0.15,
            yaw_angle=20.0,
            checks_passed=3,
        )
        liveness.analyze.return_value = result
        liveness.analyze_with_pipeline.return_value = result

        return VerificationService(
            db=db_session,
            detector=detector,
            embedder=embedder,
            liveness=liveness,
        )

    @pytest.mark.asyncio
    async def test_verify_no_face_returns_false(
        self, db_session: AsyncSession
    ):
        """Test that verification fails when no face is detected."""
        detector = MagicMock(spec=FaceDetectorService)
        detector.detect_single.return_value = (
            make_fake_detection_result(success=False, face_count=0),
            None,
        )

        embedder = FaceEmbeddingService()
        liveness = MagicMock(spec=LivenessService)

        service = VerificationService(
            db=db_session,
            detector=detector,
            embedder=embedder,
            liveness=liveness,
        )

        result = await service.verify(make_test_image_bytes(), skip_liveness=True)

        assert result.authenticated is False
        assert "No face" in (result.failure_reason or "")

    @pytest.mark.asyncio
    async def test_verify_liveness_fail_returns_false(
        self, db_session: AsyncSession
    ):
        """Test that verification fails when liveness check fails."""
        detector = MagicMock(spec=FaceDetectorService)
        detector.detect_single.return_value = (
            make_fake_detection_result(success=True),
            make_fake_detected_face(),
        )

        embedder = FaceEmbeddingService()

        liveness = MagicMock(spec=LivenessService)
        from app.services.liveness_service import LivenessCheckResult
        result = LivenessCheckResult(
            is_live=False,
            score=20.0,
            blink_detected=False,
            head_turn_detected=False,
            smile_detected=False,
            ear_value=0.30,
            mouth_ratio=0.05,
            yaw_angle=2.0,
            checks_passed=0,
            failure_reason="Blink not detected",
        )
        liveness.analyze.return_value = result
        liveness.analyze_with_pipeline.return_value = result

        service = VerificationService(
            db=db_session,
            detector=detector,
            embedder=embedder,
            liveness=liveness,
        )

        result = await service.verify(make_test_image_bytes(), skip_liveness=False)

        assert result.authenticated is False
        assert result.liveness_detail.is_live is False

    @pytest.mark.asyncio
    async def test_verify_no_enrolled_users_returns_false(
        self, db_session: AsyncSession
    ):
        """Test verification fails gracefully when no users are enrolled."""
        detector = MagicMock(spec=FaceDetectorService)
        detector.detect_single.return_value = (
            make_fake_detection_result(success=True),
            make_fake_detected_face(),
        )

        embedder = FaceEmbeddingService()
        liveness = MagicMock(spec=LivenessService)
        from app.services.liveness_service import LivenessCheckResult
        result = LivenessCheckResult(
            is_live=True, score=80.0,
            blink_detected=True, head_turn_detected=True, smile_detected=False,
            ear_value=0.25, mouth_ratio=0.10, yaw_angle=20.0, checks_passed=2,
        )
        liveness.analyze.return_value = result
        liveness.analyze_with_pipeline.return_value = result

        service = VerificationService(
            db=db_session,
            detector=detector,
            embedder=embedder,
            liveness=liveness,
        )

        result = await service.verify(
            make_test_image_bytes(),
            skip_liveness=True,
        )

        assert result.authenticated is False
        # Reason could be "No enrolled users" or "No matching face"
        assert result.failure_reason is not None

    @pytest.mark.asyncio
    async def test_verification_audit_log_created(
        self, db_session: AsyncSession
    ):
        """Test that a failed verification creates an audit log entry."""
        detector = MagicMock(spec=FaceDetectorService)
        detector.detect_single.return_value = (
            make_fake_detection_result(success=False, face_count=0),
            None,
        )

        service = VerificationService(
            db=db_session,
            detector=detector,
            embedder=FaceEmbeddingService(),
            liveness=MagicMock(spec=LivenessService),
        )

        await service.verify(make_test_image_bytes(), ip_address="1.2.3.4")

        log_repo = AuthLogRepository(db_session)
        total = await log_repo.count_total()
        assert total >= 1


class TestVerificationAPI:
    """Integration tests for verification API endpoints."""

    @pytest.mark.asyncio
    async def test_verify_endpoint_returns_200(self, async_client: AsyncClient, mock_face_detector):
        """Test POST /api/v1/verify returns 200 (with result regardless of auth outcome)."""
        with patch(
            "app.utils.dependencies.get_face_detector",
            return_value=mock_face_detector,
        ):
            image_bytes = make_test_image_bytes()

            response = await async_client.post(
                "/api/v1/verify",
                files={"image": ("face.jpg", image_bytes, "image/jpeg")},
            )

            # Should always return 200 with result object (not raise HTTP errors)
            assert response.status_code == 200
            data = response.json()
            assert "authenticated" in data
            assert "confidence_score" in data
            assert "liveness_score" in data
            assert "liveness_detail" in data

    @pytest.mark.asyncio
    async def test_verify_missing_image_returns_422(self, async_client: AsyncClient):
        """Test verification without image returns 422."""
        response = await async_client.post("/api/v1/verify")
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_verify_invalid_threshold_returns_400(self, async_client: AsyncClient, mock_face_detector):
        """Test that out-of-range threshold returns 400."""
        with patch(
            "app.utils.dependencies.get_face_detector",
            return_value=mock_face_detector,
        ):
            image_bytes = make_test_image_bytes()

            response = await async_client.post(
                "/api/v1/verify?threshold=1.5",
                files={"image": ("face.jpg", image_bytes, "image/jpeg")},
            )

            assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_verify_response_schema(self, async_client: AsyncClient, mock_face_detector):
        """Test that verification response matches expected schema."""
        with patch(
            "app.utils.dependencies.get_face_detector",
            return_value=mock_face_detector,
        ):
            image_bytes = make_test_image_bytes()

            response = await async_client.post(
                "/api/v1/verify",
                files={"image": ("face.jpg", image_bytes, "image/jpeg")},
            )

            assert response.status_code == 200
            data = response.json()

            # Required fields
            required_fields = [
                "authenticated", "confidence_score", "liveness_score",
                "liveness_detail", "threshold_used", "verified_at"
            ]
            for field in required_fields:
                assert field in data, f"Missing field: {field}"

            # Liveness detail structure
            liveness = data["liveness_detail"]
            assert "is_live" in liveness
            assert "score" in liveness
            assert "blink_detected" in liveness
            assert "head_turn_detected" in liveness
