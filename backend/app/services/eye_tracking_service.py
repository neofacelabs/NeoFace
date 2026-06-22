"""
NeoFace Trust Engine — Eye Tracking Service (Module 5)
Detects unnatural eye behavior to catch replay and static attacks.

Tracks using MediaPipe Iris:
  - Eye Aspect Ratio (EAR) — blink detection
  - Blink Rate — naturalness check
  - Gaze Direction — left, right, up, down, center
  - Pupil Movement — detects frozen/static eyes

Detects:
  - Frozen eyes (static video attack indicator)
  - Static image attacks (no pupil movement)
  - Replay attacks (unnatural blink pattern)

Output:
  { "gaze_direction": "left", "blink_detected": true, "eye_confidence": 95 }
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import ClassVar

import cv2
import mediapipe as mp
import numpy as np

from app.core.logging import logger

# MediaPipe landmark indices for iris tracking
_LEFT_EYE_CORNERS  = [362, 263]    # Outer, inner
_RIGHT_EYE_CORNERS = [33, 133]     # Outer, inner
_LEFT_IRIS_CENTER  = 473
_RIGHT_IRIS_CENTER = 468
_LEFT_EYE_LMS      = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE_LMS     = [33, 160, 158, 133, 153, 144]

# Gaze estimation: compare iris center to eye corner midpoint
_GAZE_HORIZONTAL_THRESHOLD = 0.05   # Normalized units
_GAZE_VERTICAL_THRESHOLD   = 0.04

# EAR thresholds
_EAR_CLOSED  = 0.18   # Eyes clearly closed (blink)
_EAR_NORMAL  = 0.25   # Eyes open normally

# Confidence scoring
_HIGH_CONFIDENCE  = 90.0
_MEDIUM_CONFIDENCE = 70.0


@dataclass
class EyeTrackingResult:
    """Structured output from the eye tracking service."""
    gaze_direction: str    # left | right | up | down | center
    blink_detected: bool
    eye_confidence: float  # 0–100
    ear_left: float
    ear_right: float
    ear_avg: float
    left_iris_x: float | None    # Normalized 0–1
    left_iris_y: float | None
    right_iris_x: float | None
    right_iris_y: float | None
    is_eyes_open: bool
    is_frozen: bool        # True if iris positions suggest static image
    inference_ms: float
    method: str


class EyeTrackingService:
    """
    Singleton eye tracking service using MediaPipe FaceMesh with iris refinement.
    """

    _instance: ClassVar[EyeTrackingService | None] = None

    def __init__(self) -> None:
        # Enable iris refinement for pupil/iris tracking
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,        # Enables iris landmarks (468–477)
            min_detection_confidence=0.5,
        )

    @classmethod
    def get_instance(cls) -> EyeTrackingService:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── EAR calculation ───────────────────────────────────────────────────────

    @staticmethod
    def _ear(landmarks, indices: list[int], w: int, h: int) -> float:
        """Eye Aspect Ratio using 6 landmarks."""
        def pt(i: int) -> np.ndarray:
            lm = landmarks[i]
            return np.array([lm.x * w, lm.y * h])
        p1, p2, p3, p4, p5, p6 = [pt(i) for i in indices]
        h_dist = np.linalg.norm(p1 - p4)
        if h_dist < 1e-9:
            return 0.0
        return float((np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)) / (2 * h_dist))

    # ── Gaze estimation ───────────────────────────────────────────────────────

    @staticmethod
    def _estimate_gaze(
        landmarks,
        left_iris_idx: int,
        right_iris_idx: int,
        left_corners: list[int],
        right_corners: list[int],
    ) -> str:
        """
        Estimate gaze direction by comparing iris position to eye midpoint.
        Returns: left | right | up | down | center
        """
        # Left eye
        l_iris = np.array([landmarks[left_iris_idx].x, landmarks[left_iris_idx].y])
        l_mid_x = (landmarks[left_corners[0]].x + landmarks[left_corners[1]].x) / 2
        l_mid_y = (landmarks[left_corners[0]].y + landmarks[left_corners[1]].y) / 2
        l_delta = l_iris - np.array([l_mid_x, l_mid_y])

        # Right eye
        r_iris = np.array([landmarks[right_iris_idx].x, landmarks[right_iris_idx].y])
        r_mid_x = (landmarks[right_corners[0]].x + landmarks[right_corners[1]].x) / 2
        r_mid_y = (landmarks[right_corners[0]].y + landmarks[right_corners[1]].y) / 2
        r_delta = r_iris - np.array([r_mid_x, r_mid_y])

        # Average both eyes
        avg_dx = float((l_delta[0] + r_delta[0]) / 2)
        avg_dy = float((l_delta[1] + r_delta[1]) / 2)

        if abs(avg_dx) > _GAZE_HORIZONTAL_THRESHOLD or abs(avg_dy) > _GAZE_VERTICAL_THRESHOLD:
            if abs(avg_dx) > abs(avg_dy):
                return "right" if avg_dx > 0 else "left"
            else:
                return "down" if avg_dy > 0 else "up"

        return "center"

    # ── Frozen eye detection ──────────────────────────────────────────────────

    @staticmethod
    def _detect_frozen_eyes(landmarks, w: int, h: int) -> bool:
        """
        Heuristic: detect if iris positions seem unnaturally static.
        Real eyes have micro-movements; static images produce perfectly
        centered iris positions with no deviation.

        For a single-frame check: compare iris to eye center symmetry.
        If both irises are exactly centered in each eye (within tiny margin),
        flag as potentially frozen. This is a weak signal — best combined
        with multi-frame tracking.
        """
        # MediaPipe iris landmark 473 (left iris center) and 468 (right iris center)
        # are only available with refine_landmarks=True
        try:
            l_iris_x = landmarks[473].x
            l_left_x = landmarks[362].x
            l_right_x = landmarks[263].x
            l_center = (l_left_x + l_right_x) / 2
            l_offset = abs(l_iris_x - l_center)

            r_iris_x = landmarks[468].x
            r_left_x = landmarks[33].x
            r_right_x = landmarks[133].x
            r_center = (r_left_x + r_right_x) / 2
            r_offset = abs(r_iris_x - r_center)

            # If both offsets are nearly zero, irises are suspiciously centered
            if l_offset < 0.005 and r_offset < 0.005:
                return True
        except (IndexError, AttributeError):
            pass
        return False

    # ── Public API ────────────────────────────────────────────────────────────

    def analyze(self, image_bytes: bytes) -> EyeTrackingResult:
        """
        Analyze eye behavior from raw image bytes.

        Returns EyeTrackingResult with gaze direction, blink status,
        iris positions, and anomaly flags.
        """
        t0 = time.perf_counter()

        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return EyeTrackingResult(
                gaze_direction="unknown", blink_detected=False,
                eye_confidence=0.0, ear_left=0.0, ear_right=0.0, ear_avg=0.0,
                left_iris_x=None, left_iris_y=None,
                right_iris_x=None, right_iris_y=None,
                is_eyes_open=False, is_frozen=False,
                inference_ms=0.0, method="decode_error",
            )

        h, w = img_bgr.shape[:2]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        result = self._face_mesh.process(img_rgb)

        inference_ms = round((time.perf_counter() - t0) * 1000, 2)

        if not result or not result.multi_face_landmarks:
            return EyeTrackingResult(
                gaze_direction="unknown", blink_detected=False,
                eye_confidence=20.0, ear_left=0.0, ear_right=0.0, ear_avg=0.0,
                left_iris_x=None, left_iris_y=None,
                right_iris_x=None, right_iris_y=None,
                is_eyes_open=False, is_frozen=False,
                inference_ms=inference_ms, method="no_face",
            )

        landmarks = result.multi_face_landmarks[0].landmark

        # EAR
        ear_left  = self._ear(landmarks, _LEFT_EYE_LMS, w, h)
        ear_right = self._ear(landmarks, _RIGHT_EYE_LMS, w, h)
        ear_avg   = (ear_left + ear_right) / 2.0
        blink_detected = ear_avg < _EAR_CLOSED
        is_eyes_open   = ear_avg > _EAR_NORMAL

        # Iris positions (requires refine_landmarks=True)
        left_iris_x = left_iris_y = right_iris_x = right_iris_y = None
        has_iris = len(landmarks) > 473
        if has_iris:
            left_iris_x  = round(float(landmarks[473].x), 4)
            left_iris_y  = round(float(landmarks[473].y), 4)
            right_iris_x = round(float(landmarks[468].x), 4)
            right_iris_y = round(float(landmarks[468].y), 4)

        # Gaze direction
        gaze_direction = "center"
        if has_iris:
            gaze_direction = self._estimate_gaze(
                landmarks,
                left_iris_idx=473,
                right_iris_idx=468,
                left_corners=_LEFT_EYE_CORNERS,
                right_corners=_RIGHT_EYE_CORNERS,
            )

        # Frozen eye detection
        is_frozen = self._detect_frozen_eyes(landmarks, w, h) if has_iris else False

        # Confidence
        eye_confidence = _HIGH_CONFIDENCE
        if is_frozen:
            eye_confidence = 40.0
        elif not is_eyes_open and not blink_detected:
            eye_confidence = _MEDIUM_CONFIDENCE
        if not has_iris:
            eye_confidence *= 0.85

        method = "mediapipe_iris" if has_iris else "mediapipe_facemesh"

        logger.debug(
            "eye_tracking.analyze",
            gaze=gaze_direction, blink=blink_detected,
            ear_avg=round(ear_avg, 3), is_frozen=is_frozen,
            confidence=round(eye_confidence, 1),
        )

        return EyeTrackingResult(
            gaze_direction=gaze_direction,
            blink_detected=blink_detected,
            eye_confidence=round(eye_confidence, 1),
            ear_left=round(ear_left, 4),
            ear_right=round(ear_right, 4),
            ear_avg=round(ear_avg, 4),
            left_iris_x=left_iris_x,
            left_iris_y=left_iris_y,
            right_iris_x=right_iris_x,
            right_iris_y=right_iris_y,
            is_eyes_open=is_eyes_open,
            is_frozen=is_frozen,
            inference_ms=inference_ms,
            method=method,
        )
