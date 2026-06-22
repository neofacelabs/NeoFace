"""
NeoFace Biometrics Database Persistence Tests
Verifies that enrolling iris and fingerprint records stores the raw uploaded images.
"""

from unittest.mock import MagicMock, patch
import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.fingerprint_template import FingerprintTemplate
from app.models.iris_embedding import IrisEmbedding
from app.tests.conftest import make_user_token, make_test_image_bytes


@pytest.mark.asyncio
async def test_iris_enrollment_stores_source_image_bytes(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user,
):
    """Test that iris enrollment successfully persists the source image bytes."""
    token = make_user_token(str(test_user.id), test_user.email)
    image_bytes = make_test_image_bytes()
    
    # Setup mock IrisCode returned by the processor
    mock_iris_code = MagicMock()
    mock_iris_code.code = b"iris_code_bytes_256_" + b"0" * 236
    mock_iris_code.mask = b"iris_mask_bytes_256_" + b"0" * 236
    mock_iris_code.quality_score = 85.0
    mock_iris_code.usable_bits_ratio = 0.95
    mock_iris_code.sha256 = "dummy_sha256_hash_value"

    mock_service = MagicMock()
    mock_service.process_image.return_value = mock_iris_code

    with patch("app.services.iris_service.IrisService.get_instance", return_value=mock_service):
        files = [("iris_image", ("eye.jpg", image_bytes, "image/jpeg"))]
        data = {"eye_side": "right"}
        
        response = await async_client.post(
            "/api/v1/biometrics/enroll/iris",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 201, f"Response: {response.text}"
        res_data = response.json()
        assert res_data["enrolled"] is True
        
        # Query database directly to confirm source_image_bytes is saved
        result = await db_session.execute(
            select(IrisEmbedding).where(IrisEmbedding.user_id == test_user.id)
        )
        records = list(result.scalars().all())
        assert len(records) == 1
        assert records[0].source_image_bytes == image_bytes


@pytest.mark.asyncio
async def test_fingerprint_enrollment_stores_source_image_bytes(
    async_client: AsyncClient,
    db_session: AsyncSession,
    test_user,
):
    """Test that fingerprint enrollment successfully persists the source image bytes."""
    token = make_user_token(str(test_user.id), test_user.email)
    image_bytes = make_test_image_bytes()
    
    # Setup mock fingerprint template returned by the processor
    mock_template = MagicMock()
    mock_template.minutiae_count = 25
    mock_template.quality_score = 90.0
    mock_template.to_bytes.return_value = b"fingerprint_template_data"
    mock_template.sha256 = "dummy_fingerprint_sha256_hash"

    mock_service = MagicMock()
    mock_service.extract_minutiae.return_value = mock_template

    with patch("app.services.fingerprint_service.FingerprintService.get_instance", return_value=mock_service):
        files = [("fingerprint_image", ("finger.jpg", image_bytes, "image/jpeg"))]
        data = {"finger_position": 2, "impression_type": "live_scan"}
        
        response = await async_client.post(
            "/api/v1/biometrics/enroll/fingerprint",
            data=data,
            files=files,
            headers={"Authorization": f"Bearer {token}"},
        )
        
        assert response.status_code == 201, f"Response: {response.text}"
        res_data = response.json()
        assert res_data["enrolled"] is True
        
        # Query database directly to confirm source_image_bytes is saved
        result = await db_session.execute(
            select(FingerprintTemplate).where(FingerprintTemplate.user_id == test_user.id)
        )
        records = list(result.scalars().all())
        assert len(records) == 1
        assert records[0].source_image_bytes == image_bytes
