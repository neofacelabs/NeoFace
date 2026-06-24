"""
NeoFace Face Detection Service
Uses InsightFace FaceAnalysis (buffalo_l model) for:
- Face detection
- Facial landmark extraction
- Quality estimation
- Face cropping and alignment

Singleton pattern — model is loaded once at startup.
"""

from __future__ import annotations

import io
from dataclasses import dataclass, field
from typing import ClassVar

import cv2
import numpy as np
from insightface.app import FaceAnalysis

from app.core.config import settings
from app.core.logging import logger


@dataclass
class DetectedFace:
    """Structured result from face detection on a single face."""

    bbox: tuple[int, int, int, int]       # (x1, y1, x2, y2)
    landmarks: np.ndarray                  # 5-point landmarks (5, 2)
    embedding: np.ndarray | None           # 512-d ArcFace embedding (if available)
    detection_score: float                 # Detector confidence (0–1)
    quality_score: float                   # Estimated face quality (0–100)
    face_crop: np.ndarray                  # Aligned face BGR crop (112x112)


@dataclass
class DetectionResult:
    """Full detection result for a single image."""

    success: bool
    face_count: int
    faces: list[DetectedFace] = field(default_factory=list)
    error: str | None = None
    image_width: int = 0
    image_height: int = 0
    blur_score: float = 0.0


class FaceDetectorService:
    """
    Singleton face detection service backed by InsightFace buffalo_l.

    Usage:
        detector = FaceDetectorService.get_instance()
        result = await detector.detect(image_bytes)
    """

    _instance: ClassVar[FaceDetectorService | None] = None
    _initialized: ClassVar[bool] = False

    def __init__(self) -> None:
        self._model: FaceAnalysis | None = None

    @classmethod
    def get_instance(cls) -> FaceDetectorService:
        """Return the global singleton, initializing on first call."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def initialize(self) -> None:
        """
        Load InsightFace model into memory.
        Called once during application startup.
        CPU-only for MVP; GPU-enabled via ctx_id=0 in production.
        """
        if self._initialized:
            return

        logger.info("Loading InsightFace model", model=settings.FACE_DETECTION_MODEL)
        try:
            import os
            import warnings

            # InsightFace internally probes CUDAExecutionProvider even in CPU mode
            # (ctx_id=-1).  The provider is unavailable in this environment, which
            # triggers a noisy-but-harmless UserWarning from onnxruntime.  Suppress
            # it so logs stay clean.
            os.environ.setdefault("ORT_LOGGING_LEVEL", "3")  # ERROR-only
            warnings.filterwarnings(
                "ignore",
                message=".*CUDAExecutionProvider.*",
                category=UserWarning,
            )

            insightface_root = os.environ.get("INSIGHTFACE_HOME", os.path.expanduser("~/.insightface"))
            self._model = FaceAnalysis(
                name=settings.FACE_DETECTION_MODEL,
                allowed_modules=["detection", "recognition"],
                root=insightface_root,
            )
            # ctx_id=-1 = CPU; set ctx_id=0 for GPU
            self._model.prepare(
                ctx_id=-1,
                det_thresh=settings.DETECTION_THRESHOLD,
                det_size=(640, 640)
            )
            FaceDetectorService._initialized = True
            logger.info("InsightFace model loaded successfully")
        except Exception as exc:
            logger.error("Failed to load InsightFace model", error=str(exc))
            raise RuntimeError(f"Face detection model failed to load: {exc}") from exc

    def _bytes_to_bgr(self, image_bytes: bytes) -> np.ndarray:
        """Decode image bytes to OpenCV BGR array."""
        nparr = np.frombuffer(image_bytes, np.uint8)
        img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        if img is None:
            raise ValueError("Could not decode image — unsupported format or corrupt file")
        return img

    def _compute_blur_score(self, img: np.ndarray) -> float:
        """
        Compute Laplacian variance as blur metric.
        Higher = sharper image. Threshold: settings.BLUR_THRESHOLD.
        """
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        return float(cv2.Laplacian(gray, cv2.CV_64F).var())

    def _estimate_face_quality(self, face, img: np.ndarray) -> float:
        """
        Estimate face quality score (0–100).
        Combines:
        - Detector confidence
        - Face size relative to image
        - Blur score of face crop
        """
        score = face.det_score * 40  # Base: detection confidence contributes 40 pts

        # Size contribution: larger faces = better quality (up to 40 pts)
        h, w = img.shape[:2]
        x1, y1, x2, y2 = face.bbox.astype(int)
        face_area = (x2 - x1) * (y2 - y1)
        image_area = h * w
        if image_area > 0:
            size_ratio = face_area / image_area
            score += min(size_ratio * 200, 40)

        # Blur contribution: up to 20 pts
        face_crop = img[max(0, y1):y2, max(0, x1):x2]
        if face_crop.size > 0:
            blur = float(cv2.Laplacian(cv2.cvtColor(face_crop, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var())
            score += min(blur / settings.BLUR_THRESHOLD * 20, 20)

        return min(float(score), 100.0)

    def detect(self, image_bytes: bytes) -> DetectionResult:
        """
        Detect all faces in an image.

        Args:
            image_bytes: Raw image file bytes (JPEG, PNG, etc.)

        Returns:
            DetectionResult with all detected faces and metadata.
        """
        if not self._initialized or self._model is None:
            raise RuntimeError("FaceDetectorService not initialized. Call initialize() first.")

        try:
            img = self._bytes_to_bgr(image_bytes)
        except ValueError as exc:
            return DetectionResult(success=False, face_count=0, error=str(exc))

        h, w = img.shape[:2]
        blur_score = self._compute_blur_score(img)

        # ── Image quality checks ──────────────────────────────────────────────
        if w < settings.MIN_IMAGE_WIDTH or h < settings.MIN_IMAGE_HEIGHT:
            logger.warning(f"Image too small: {w}x{h}, minimum {settings.MIN_IMAGE_WIDTH}x{settings.MIN_IMAGE_HEIGHT}")
            return DetectionResult(
                success=False,
                face_count=0,
                error=f"Image too small: {w}x{h}, minimum {settings.MIN_IMAGE_WIDTH}x{settings.MIN_IMAGE_HEIGHT}",
                image_width=w,
                image_height=h,
                blur_score=blur_score,
            )

        if blur_score < settings.BLUR_THRESHOLD:
            logger.warning(f"Blurry image rejected: score={blur_score:.1f}, threshold={settings.BLUR_THRESHOLD}")
            return DetectionResult(
                success=False,
                face_count=0,
                error=f"Image too blurry (score={blur_score:.1f}, threshold={settings.BLUR_THRESHOLD})",
                image_width=w,
                image_height=h,
                blur_score=blur_score,
            )

        # ── Run InsightFace detection ─────────────────────────────────────────
        try:
            faces_raw = self._model.get(img)
        except Exception as exc:
            logger.error("InsightFace detection error", error=str(exc))
            return DetectionResult(
                success=False,
                face_count=0,
                error=f"Detection error: {exc}",
                image_width=w,
                image_height=h,
                blur_score=blur_score,
            )

        if not faces_raw:
            logger.warning("FaceDetectorService: No faces detected in image by InsightFace")
            return DetectionResult(
                success=False,
                face_count=0,
                error="No face detected in the image",
                image_width=w,
                image_height=h,
                blur_score=blur_score,
            )

        # ── Build structured results ──────────────────────────────────────────
        detected_faces: list[DetectedFace] = []
        for face in faces_raw:
            x1, y1, x2, y2 = face.bbox.astype(int)
            # Clamp to image bounds
            x1, y1 = max(0, x1), max(0, y1)
            x2, y2 = min(w, x2), min(h, y2)
            face_crop = img[y1:y2, x1:x2]
            face_crop_resized = cv2.resize(face_crop, (112, 112)) if face_crop.size > 0 else np.zeros((112, 112, 3), dtype=np.uint8)

            quality = self._estimate_face_quality(face, img)

            detected_faces.append(
                DetectedFace(
                    bbox=(x1, y1, x2, y2),
                    landmarks=face.kps if hasattr(face, "kps") and face.kps is not None else np.zeros((5, 2)),
                    embedding=face.embedding if hasattr(face, "embedding") else None,
                    detection_score=float(face.det_score),
                    quality_score=quality,
                    face_crop=face_crop_resized,
                )
            )

        return DetectionResult(
            success=True,
            face_count=len(detected_faces),
            faces=detected_faces,
            image_width=w,
            image_height=h,
            blur_score=blur_score,
        )

    def detect_single(self, image_bytes: bytes) -> tuple[DetectionResult, "DetectedFace | None"]:
        """
        Detect and return exactly one face (the highest-confidence one).
        Falls back gracefully when there are multiple faces — picks the best.
        Fails only when no face is found at all.

        Returns (result, face) — face is None on failure.
        """
        result = self.detect(image_bytes)

        if not result.success:
            return result, None

        if result.face_count == 0:
            result.success = False
            result.error = "No face detected"
            return result, None

        # Pick the highest-confidence face (works for both 1 and multi-face frames)
        best_face = max(result.faces, key=lambda f: f.detection_score)
        return result, best_face
