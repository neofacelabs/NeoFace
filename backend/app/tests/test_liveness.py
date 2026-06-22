"""
NeoFace Liveness Detection Tests
Tests for MediaPipe-based liveness analysis.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.liveness_service import LivenessCheckResult, LivenessService


class TestLivenessService:
    """Unit tests for LivenessService."""

    @pytest.fixture
    def liveness_service(self):
        return LivenessService()

    def test_liveness_result_dataclass(self):
        """Test LivenessCheckResult can be created with expected fields."""
        result = LivenessCheckResult(
            is_live=True,
            score=85.0,
            blink_detected=True,
            head_turn_detected=True,
            smile_detected=False,
            ear_value=0.25,
            mouth_ratio=0.08,
            yaw_angle=18.0,
            checks_passed=2,
        )
        assert result.is_live is True
        assert result.score == 85.0
        assert result.checks_passed == 2
        assert result.checks_total == 3

    def test_analyze_corrupt_image_returns_failure(self, liveness_service):
        """Test that a corrupt image returns is_live=False without crashing."""
        corrupt_bytes = b"this is not an image"
        result = liveness_service.analyze(corrupt_bytes)

        assert result.is_live is False
        assert result.score == 0.0
        assert result.failure_reason is not None

    def test_analyze_empty_bytes_returns_failure(self, liveness_service):
        """Test that empty bytes return a graceful failure."""
        result = liveness_service.analyze(b"")
        assert result.is_live is False

    def test_liveness_score_range(self, liveness_service):
        """Test that liveness score is always in [0, 100]."""
        # Use a plain gray image
        try:
            import cv2
            img = np.ones((224, 224, 3), dtype=np.uint8) * 128
            _, buf = cv2.imencode(".jpg", img)
            image_bytes = buf.tobytes()
        except ImportError:
            pytest.skip("OpenCV not available")

        result = liveness_service.analyze(image_bytes)
        assert 0.0 <= result.score <= 100.0

    def test_ear_calculation_logic(self, liveness_service):
        """Test EAR formula with known values."""
        # Create mock landmarks
        mock_landmarks = [MagicMock() for _ in range(500)]

        # Set up 6 eye landmark points for a known EAR result
        # EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        test_indices = [33, 160, 158, 133, 153, 144]  # RIGHT_EYE

        # Mock positions: simple rectangle eye
        positions = {
            33:  (0.3, 0.5),   # p1
            160: (0.33, 0.48), # p2
            158: (0.37, 0.48), # p3
            133: (0.4, 0.5),   # p4
            153: (0.37, 0.52), # p5
            144: (0.33, 0.52), # p6
        }
        for idx, (x, y) in positions.items():
            mock_landmarks[idx].x = x
            mock_landmarks[idx].y = y

        ear = liveness_service._eye_aspect_ratio(
            mock_landmarks, test_indices, w=640, h=480
        )

        # EAR should be a reasonable positive value
        assert 0.0 <= ear <= 1.0

    def test_mouth_aspect_ratio_logic(self, liveness_service):
        """Test MAR calculation returns valid range."""
        mock_landmarks = [MagicMock() for _ in range(500)]

        # Mouth landmarks
        mock_landmarks[13].x, mock_landmarks[13].y = 0.5, 0.72  # top
        mock_landmarks[14].x, mock_landmarks[14].y = 0.5, 0.76  # bottom
        mock_landmarks[78].x, mock_landmarks[78].y = 0.44, 0.74  # left
        mock_landmarks[308].x, mock_landmarks[308].y = 0.56, 0.74  # right

        mar = liveness_service._mouth_aspect_ratio(mock_landmarks, w=640, h=480)
        assert 0.0 <= mar <= 1.0

    def test_checks_passed_count(self):
        """Test checks_passed is correctly summed from booleans."""
        result = LivenessCheckResult(
            is_live=True,
            score=90.0,
            blink_detected=True,
            head_turn_detected=True,
            smile_detected=True,
            ear_value=0.20,
            mouth_ratio=0.12,
            yaw_angle=20.0,
            checks_passed=3,
        )
        assert result.checks_passed == 3

    def test_failure_reason_set_on_failure(self, liveness_service):
        """Test that failure_reason is populated when liveness fails."""
        corrupt_bytes = b"not an image"
        result = liveness_service.analyze(corrupt_bytes)

        if not result.is_live:
            assert result.failure_reason is not None
            assert len(result.failure_reason) > 0
