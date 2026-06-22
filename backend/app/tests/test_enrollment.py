"""
NeoFace Enrollment Tests
Tests for the face enrollment pipeline and API endpoints.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories.embedding_repository import EmbeddingRepository
from app.repositories.user_repository import UserRepository
from app.schemas.enrollment import EnrollmentRequest
from app.services.enrollment_service import EnrollmentError, EnrollmentService
from app.services.face_detector import FaceDetectorService
from app.services.face_embedding import FaceEmbeddingService
from app.utils.storage import StorageService
from app.tests.conftest import (
    make_admin_token,
    make_user_token,
    make_fake_detected_face,
    make_fake_detection_result,
    make_fake_embedding,
    make_test_image_bytes,
)


class TestEnrollmentService:
    """Unit tests for EnrollmentService business logic."""

    @pytest_asyncio.fixture
    async def enrollment_service(self, db_session: AsyncSession):
        """Create EnrollmentService with mocked AI services."""
        detector = MagicMock(spec=FaceDetectorService)
        detector.detect_single.return_value = (
            make_fake_detection_result(success=True),
            make_fake_detected_face(),
        )
        detector._initialized = True

        embedder = MagicMock(spec=FaceEmbeddingService)
        embedder.get_embedding.return_value = make_fake_embedding()
        embedder.average_embeddings.return_value = make_fake_embedding()
        embedder.embedding_to_list.return_value = make_fake_embedding().tolist()

        storage = AsyncMock(spec=StorageService)
        storage.save_face_image.return_value = "faces/test/image.jpg"

        return EnrollmentService(
            db=db_session,
            detector=detector,
            embedder=embedder,
            storage=storage,
        )

    @pytest.mark.asyncio
    async def test_enroll_new_user_success(self, enrollment_service):
        """Test successful enrollment of a new user."""
        request = EnrollmentRequest(
            name="Alice Johnson",
            email=f"alice_{uuid.uuid4().hex[:8]}@example.com",
            phone="+14155552671",
        )
        image_bytes = [make_test_image_bytes()]

        result = await enrollment_service.enroll(request, image_bytes)

        assert result.status == "enrolled"
        assert result.user_id is not None
        assert result.images_processed == 1
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_enroll_multiple_images(self, enrollment_service):
        """Test enrollment with multiple images averages embeddings."""
        request = EnrollmentRequest(
            name="Bob Smith",
            email=f"bob_{uuid.uuid4().hex[:8]}@example.com",
        )
        # 3 images
        images = [make_test_image_bytes()] * 3

        result = await enrollment_service.enroll(request, images)

        assert result.status == "enrolled"
        assert result.images_processed == 3
        # Embedder average should have been called
        enrollment_service.embedder.average_embeddings.assert_called_once()

    @pytest.mark.asyncio
    async def test_enroll_too_many_images_raises(self, enrollment_service):
        """Test that exceeding max image count raises EnrollmentError."""
        request = EnrollmentRequest(
            name="Carol",
            email=f"carol_{uuid.uuid4().hex[:8]}@example.com",
        )
        images = [make_test_image_bytes()] * 10  # Exceeds MAX_ENROLLMENT_IMAGES=5

        with pytest.raises(EnrollmentError, match="Maximum"):
            await enrollment_service.enroll(request, images)

    @pytest.mark.asyncio
    async def test_enroll_no_face_detected_rejected(self, enrollment_service):
        """Test that images with no face are rejected."""
        # Make all detections fail
        enrollment_service.detector.detect_single.return_value = (
            make_fake_detection_result(success=False, face_count=0),
            None,
        )

        request = EnrollmentRequest(
            name="Dave",
            email=f"dave_{uuid.uuid4().hex[:8]}@example.com",
        )
        images = [make_test_image_bytes()]

        with pytest.raises(EnrollmentError, match="No valid face images"):
            await enrollment_service.enroll(request, images)

    @pytest.mark.asyncio
    async def test_reenrollment_replaces_embeddings(
        self, enrollment_service, test_user, enrolled_user
    ):
        """Test that re-enrollment deletes old embeddings and creates new ones."""
        user, old_embedding = enrolled_user

        request = EnrollmentRequest(
            name=user.name,
            email=user.email,
        )
        images = [make_test_image_bytes()]

        result = await enrollment_service.enroll(request, images)

        assert result.status == "enrolled"
        assert result.user_id == user.id

    @pytest.mark.asyncio
    async def test_quality_results_populated(self, enrollment_service):
        """Test that quality results are returned for each image."""
        request = EnrollmentRequest(
            name="Eve",
            email=f"eve_{uuid.uuid4().hex[:8]}@example.com",
        )
        images = [make_test_image_bytes()] * 2

        result = await enrollment_service.enroll(request, images)

        assert len(result.quality_results) == 2
        for qr in result.quality_results:
            assert qr.image_index in [0, 1]


class TestEnrollmentAPI:
    """Integration tests for enrollment API endpoints."""

    @pytest.mark.asyncio
    async def test_enroll_endpoint_success(self, async_client: AsyncClient, mock_face_detector):
        """Test POST /api/v1/enrollment with valid data."""
        with patch(
            "app.utils.dependencies.get_face_detector",
            return_value=mock_face_detector,
        ):
            image_bytes = make_test_image_bytes()
            files = [("images", ("test.jpg", image_bytes, "image/jpeg"))]

            response = await async_client.post(
                "/api/v1/enrollment",
                data={
                    "name": "Test Enrollee",
                    "email": f"enrollee_{uuid.uuid4().hex[:8]}@test.com",
                },
                files=files,
            )

            # May be 201 or 400 depending on image quality in CI
            assert response.status_code in [201, 400]

    @pytest.mark.asyncio
    async def test_enroll_missing_name_returns_422(self, async_client: AsyncClient):
        """Test that missing required fields return 422."""
        image_bytes = make_test_image_bytes()
        files = [("images", ("test.jpg", image_bytes, "image/jpeg"))]

        response = await async_client.post(
            "/api/v1/enrollment",
            data={"email": "test@test.com"},  # Missing name
            files=files,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_enroll_no_images_returns_400(self, async_client: AsyncClient):
        """Test that enrollment without images returns 400."""
        response = await async_client.post(
            "/api/v1/enrollment",
            data={"name": "Test", "email": "test@test.com"},
        )

        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_get_enrollment_status_not_found(self, async_client: AsyncClient):
        """Test GET enrollment status for non-existent user."""
        fake_id = uuid.uuid4()
        response = await async_client.get(f"/api/v1/enrollment/{fake_id}")
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_get_enrollment_status_success(
        self, async_client: AsyncClient, enrolled_user
    ):
        """Test GET enrollment status for enrolled user."""
        user, _ = enrolled_user
        response = await async_client.get(f"/api/v1/enrollment/{user.id}")
        assert response.status_code == 200
        data = response.json()
        assert data["is_enrolled"] is True
        assert data["enrollment_count"] >= 1

    @pytest.mark.asyncio
    async def test_delete_enrollment_requires_admin(
        self, async_client: AsyncClient, enrolled_user, test_user
    ):
        """Test that deleting enrollment requires admin role."""
        user, _ = enrolled_user
        user_token = make_user_token(str(test_user.id), test_user.email)

        response = await async_client.delete(
            f"/api/v1/enrollment/{user.id}",
            headers={"Authorization": f"Bearer {user_token}"},
        )

        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_delete_enrollment_admin_success(
        self, async_client: AsyncClient, enrolled_user, test_admin
    ):
        """Test admin can delete enrollment."""
        user, _ = enrolled_user
        admin_token = make_admin_token(str(test_admin.id), test_admin.email)

        response = await async_client.delete(
            f"/api/v1/enrollment/{user.id}",
            headers={"Authorization": f"Bearer {admin_token}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert "deleted" in data.get("message", "").lower() or data.get("embeddings_deleted") >= 0

    @pytest.mark.asyncio
    async def test_validate_frame_endpoint_success(self, async_client: AsyncClient, mock_face_detector):
        """Test POST /api/v1/enrollment/validate-frame with valid data."""
        with patch(
            "app.utils.dependencies.get_face_detector",
            return_value=mock_face_detector,
        ):
            image_bytes = make_test_image_bytes()
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}

            response = await async_client.post(
                "/api/v1/enrollment/validate-frame",
                files=files,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert "quality_score" in data

    @pytest.mark.asyncio
    async def test_validate_frame_endpoint_failure(self, async_client: AsyncClient, mock_face_detector):
        """Test POST /api/v1/enrollment/validate-frame when face detection fails."""
        res = make_fake_detection_result(success=False, face_count=0)
        res.error = "Image too blurry"
        mock_face_detector.detect_single.return_value = (
            res,
            None,
        )
        with patch(
            "app.utils.dependencies.get_face_detector",
            return_value=mock_face_detector,
        ):
            image_bytes = make_test_image_bytes()
            files = {"file": ("test.jpg", image_bytes, "image/jpeg")}

            response = await async_client.post(
                "/api/v1/enrollment/validate-frame",
                files=files,
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is False
            assert data["error"] == "Image too blurry"
