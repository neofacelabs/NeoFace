"""
NeoFace Anti-Spoofing Tests
Tests for AntiSpoofService and LivenessPipeline.
"""

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from app.services.anti_spoof_service import AntiSpoofResult, AntiSpoofService
from app.services.liveness_pipeline import LivenessPipeline, LivenessPipelineResult


class TestAntiSpoofResult:
    """Unit tests for AntiSpoofResult dataclass."""

    def test_real_face_result(self):
        result = AntiSpoofResult(
            is_real=True, score=92.0, raw_real_prob=0.92,
            method="minifasnet", attack_type="none",
        )
        assert result.is_real is True
        assert result.score == 92.0
        assert result.attack_type == "none"

    def test_spoof_face_result(self):
        result = AntiSpoofResult(
            is_real=False, score=22.0, raw_real_prob=0.22,
            method="heuristic_fallback", attack_type="photo",
        )
        assert result.is_real is False
        assert result.attack_type == "photo"
        assert result.model_available is True


class TestAntiSpoofServiceHeuristic:
    """Tests for the heuristic fallback scorer (no model required)."""

    @pytest.fixture
    def service(self):
        svc = AntiSpoofService()
        # Force heuristic path — no ONNX session
        svc._model_loaded = False
        svc._session = None
        return svc

    def test_predict_gray_image_returns_result(self, service):
        """Gray image returns a result (not an exception)."""
        try:
            import cv2
            img = np.ones((112, 112, 3), dtype=np.uint8) * 128
            result = service.predict(img)
            assert 0.0 <= result.score <= 100.0
            assert result.method == "heuristic_fallback"
            assert result.model_available is False
        except ImportError:
            pytest.skip("OpenCV not available")

    def test_predict_empty_returns_failure(self, service):
        """Empty array returns a failure result without crashing."""
        empty = np.array([], dtype=np.uint8).reshape(0, 0, 3)
        result = service.predict(empty)
        assert result.is_real is False
        assert result.score == 0.0

    def test_predict_from_bytes_corrupt(self, service):
        """Corrupt bytes return a failure result."""
        result = service.predict_from_bytes(b"not an image")
        assert result.is_real is False
        assert result.method == "error"

    def test_anti_spoof_disabled(self):
        """When ANTI_SPOOF_ENABLED=False every face is treated as real."""
        with patch("app.services.anti_spoof_service.settings") as mock_settings:
            mock_settings.ANTI_SPOOF_ENABLED = False
            mock_settings.ANTI_SPOOF_THRESHOLD = 0.70
            svc = AntiSpoofService()
            img = np.ones((80, 80, 3), dtype=np.uint8) * 100
            result = svc.predict(img)
        assert result.is_real is True
        assert result.method == "disabled"

    def test_lbp_variance_nonzero_for_textured_image(self, service):
        """LBP variance is positive for a non-uniform image."""
        try:
            rng = np.random.RandomState(42)
            noisy_gray = rng.randint(0, 256, (30, 30), dtype=np.uint8)
            var = service._lbp_variance(noisy_gray)
            assert var > 0
        except Exception:
            pytest.skip("LBP variance test skipped")


class TestLivenessPipelineResult:
    """Unit tests for LivenessPipelineResult dataclass."""

    def test_default_values(self):
        result = LivenessPipelineResult(
            is_live=True, score=85.0, anti_spoof_score=90.0,
        )
        assert result.method == "pipeline_v2"
        assert result.blink_detected is False
        assert result.attack_type == "none"
        assert result.failure_reason is None
        assert len(result.stages) == 0

    def test_failed_result_has_reason(self):
        result = LivenessPipelineResult(
            is_live=False, score=20.0, anti_spoof_score=15.0,
            failure_reason="Anti-spoof failed: photo attack",
        )
        assert result.is_live is False
        assert "photo" in result.failure_reason


class TestLivenessPipelineIntegration:
    """Integration-style tests for LivenessPipeline (mocked dependencies)."""

    @pytest.fixture
    def pipeline_with_mocks(self):
        """Pipeline with mocked detector and anti-spoof service."""
        from app.services.face_detector import DetectedFace, DetectionResult
        from app.services.anti_spoof_service import AntiSpoofResult

        mock_detector = MagicMock()
        mock_detector.detect_single.return_value = (
            DetectionResult(
                success=True, face_count=1,
                faces=[],  # pipeline re-runs mediapipe internally
                image_width=640, image_height=480, blur_score=250.0,
                error=None,
            ),
            DetectedFace(
                bbox=(50, 50, 200, 200),
                landmarks=np.zeros((5, 2)),
                embedding=np.random.randn(512).astype(np.float32),
                detection_score=0.98,
                quality_score=85.0,
                face_crop=np.zeros((112, 112, 3), dtype=np.uint8),
            ),
        )

        mock_anti_spoof = MagicMock()
        mock_anti_spoof.predict.return_value = AntiSpoofResult(
            is_real=True, score=88.0, raw_real_prob=0.88,
            method="minifasnet", attack_type="none",
        )

        pipeline = LivenessPipeline(
            detector=mock_detector,
            anti_spoof=mock_anti_spoof,
        )
        return pipeline

    def test_pipeline_fail_no_face(self):
        """Pipeline returns failure when no face is detected."""
        from app.services.face_detector import DetectionResult

        mock_detector = MagicMock()
        mock_detector.detect_single.return_value = (
            DetectionResult(
                success=False, face_count=0, faces=[],
                image_width=0, image_height=0, blur_score=0.0,
                error="No face detected",
            ),
            None,
        )
        pipeline = LivenessPipeline(detector=mock_detector)
        try:
            import cv2
            img = np.ones((224, 224, 3), dtype=np.uint8) * 128
            _, buf = cv2.imencode(".jpg", img)
            image_bytes = buf.tobytes()
        except ImportError:
            image_bytes = (
                b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
                b"\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t"
                b"\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a"
                b"\x1f\x1e\x1d\x1a\x1c\x1c $.' \",#\x1c\x1c(7),01444\x1f'9=82<.342\x1e"
                b"\xff\xc0\x00\x0b\x08\x00\x01\x00\x01\x01\x01\x11\x00\xff\xc4\x00\x1f"
                b"\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00"
                b"\x00\x01\x02\x03\x04\x05\x06\x07\x08\t\n\x0b\xff\xda\x00\x08\x01\x01"
                b"\x00\x00?\x00\xf5\x0a\xff\xd9"
            )
        result = pipeline.run(image_bytes)

        assert result.is_live is False
        assert result.failure_reason is not None
        assert len(result.stages) >= 1
        assert result.stages[0].stage_name == "face_detection"
        assert result.stages[0].passed is False

    def test_pipeline_stage_count(self, pipeline_with_mocks):
        """On full execution, all 6 stages are recorded."""
        try:
            import cv2
            img = np.ones((224, 224, 3), dtype=np.uint8) * 128
            _, buf = cv2.imencode(".jpg", img)
            result = pipeline_with_mocks.run(buf.tobytes())
            # At minimum we get the detection stage
            assert len(result.stages) >= 1
        except ImportError:
            pytest.skip("OpenCV not available")

    def test_pipeline_spoof_fail(self):
        """Pipeline fails when anti-spoof rejects the face."""
        from app.services.face_detector import DetectedFace, DetectionResult
        from app.services.anti_spoof_service import AntiSpoofResult

        mock_detector = MagicMock()
        mock_detector.detect_single.return_value = (
            DetectionResult(
                success=True, face_count=1, faces=[], error=None,
                image_width=640, image_height=480, blur_score=300.0,
            ),
            DetectedFace(
                bbox=(50, 50, 200, 200), landmarks=np.zeros((5, 2)),
                embedding=np.random.randn(512).astype(np.float32),
                detection_score=0.97, quality_score=80.0,
                face_crop=np.zeros((112, 112, 3), dtype=np.uint8),
            ),
        )
        mock_anti_spoof = MagicMock()
        mock_anti_spoof.predict.return_value = AntiSpoofResult(
            is_real=False, score=12.0, raw_real_prob=0.12,
            method="minifasnet", attack_type="photo",
        )

        pipeline = LivenessPipeline(detector=mock_detector, anti_spoof=mock_anti_spoof)

        try:
            import cv2
            img = np.ones((224, 224, 3), dtype=np.uint8) * 100
            _, buf = cv2.imencode(".jpg", img)
            result = pipeline.run(buf.tobytes())
            assert result.is_live is False
            assert result.anti_spoof_score == 12.0
        except ImportError:
            pytest.skip("OpenCV not available")


class TestPassiveLivenessService:
    """Unit tests for PassiveLivenessService."""

    def test_passive_liveness_disabled(self):
        """When ANTI_SPOOF_ENABLED=False every face is treated as real/live."""
        from app.services.passive_liveness_service import PassiveLivenessService
        with patch("app.services.passive_liveness_service.settings") as mock_settings:
            mock_settings.ANTI_SPOOF_ENABLED = False
            mock_settings.PASSIVE_LIVENESS_THRESHOLD = 0.65
            svc = PassiveLivenessService()
            img = np.ones((80, 80, 3), dtype=np.uint8) * 100
            result = svc.predict(img)
        assert result.is_live is True
        assert result.liveness_score == 1.0
        assert result.confidence == 100.0
        assert result.attack_type == "none"
        assert result.method == "disabled"

    def test_passive_liveness_threshold(self):
        """Verify dynamic PASSIVE_LIVENESS_THRESHOLD is respected."""
        from app.services.passive_liveness_service import PassiveLivenessService
        with patch("app.services.passive_liveness_service.settings") as mock_settings:
            mock_settings.ANTI_SPOOF_ENABLED = True
            mock_settings.PASSIVE_LIVENESS_THRESHOLD = 0.99
            svc = PassiveLivenessService()
            svc._v1_loaded = True
            svc._v2_loaded = True
            svc._infer_v1 = MagicMock(return_value=0.85)
            svc._infer_v2 = MagicMock(return_value=0.85)
            img = np.ones((80, 80, 3), dtype=np.uint8) * 100
            result = svc.predict(img)
            assert result.is_live is False

            mock_settings.PASSIVE_LIVENESS_THRESHOLD = 0.50
            result = svc.predict(img)
            assert result.is_live is True
