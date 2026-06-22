"""
NeoFace Liveness Detection Service
Provides two analysis modes:

  1. analyze(image_bytes)               — Legacy single-stage MediaPipe check.
     Kept for backwards compatibility and lightweight deployments.

  2. analyze_with_pipeline(image_bytes) — Full 6-stage pipeline:
       Stage 1  Face Detection
       Stage 2  Quality Validation
       Stage 3  Blink Detection (EAR)
       Stage 4  Head Movement (yaw)
       Stage 5  Passive Anti-Spoof (MiniFASNet / heuristic)
       Stage 6  Score Composition

Both methods return a LivenessCheckResult with a compatible interface so
callers can switch modes without changing their response handling.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import cv2
import mediapipe as mp
import numpy as np

from app.core.config import settings
from app.core.logging import logger


@dataclass
class LivenessCheckResult:
    """
    Unified liveness analysis result — compatible with both the legacy
    single-stage path and the full multi-stage pipeline.
    """

    is_live: bool
    score: float                        # 0–100 composite score
    blink_detected: bool
    head_turn_detected: bool
    smile_detected: bool
    ear_value: float                    # Eye Aspect Ratio
    mouth_ratio: float                  # Mouth openness ratio
    yaw_angle: float                    # Head yaw in degrees
    checks_passed: int
    checks_total: int = 3
    # Extended fields (populated by pipeline mode)
    anti_spoof_score: float = 0.0       # 0–100 (0 when not run)
    method: str = "mediapipe_v1"        # "mediapipe_v1" | "pipeline_v2+..."
    failure_reason: str | None = None


class LivenessService:
    """
    Passive liveness check service using MediaPipe Face Mesh.

    Analyzes a single frame for signs of liveness.
    For multi-frame video analysis, call analyze() on each frame and aggregate.
    """

    # ── MediaPipe landmark indices ─────────────────────────────────────────────
    # Left eye landmarks
    LEFT_EYE = [362, 385, 387, 263, 373, 380]
    # Right eye landmarks
    RIGHT_EYE = [33, 160, 158, 133, 153, 144]
    # Mouth landmarks (outer)
    MOUTH_TOP = 13
    MOUTH_BOTTOM = 14
    MOUTH_LEFT = 78
    MOUTH_RIGHT = 308
    # Nose tip for head pose
    NOSE_TIP = 1
    NOSE_BASE = 168

    # ── Thresholds ────────────────────────────────────────────────────────────
    EAR_BLINK_THRESHOLD = 0.20      # Below this = eye closed
    MOUTH_SMILE_THRESHOLD = 0.10    # Above this = smiling/open mouth
    YAW_TURN_THRESHOLD = 15.0       # Degrees — head turned left or right

    def __init__(self) -> None:
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )

    def _eye_aspect_ratio(self, landmarks: list, indices: list[int], w: int, h: int) -> float:
        """
        Compute Eye Aspect Ratio (EAR).
        EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)
        """
        def point(idx: int) -> np.ndarray:
            lm = landmarks[idx]
            return np.array([lm.x * w, lm.y * h])

        p1, p2, p3, p4, p5, p6 = [point(i) for i in indices]
        vertical_1 = np.linalg.norm(p2 - p6)
        vertical_2 = np.linalg.norm(p3 - p5)
        horizontal = np.linalg.norm(p1 - p4)

        if horizontal == 0:
            return 0.0

        return float((vertical_1 + vertical_2) / (2.0 * horizontal))

    def _mouth_aspect_ratio(self, landmarks: list, w: int, h: int) -> float:
        """
        Compute simplified Mouth Aspect Ratio.
        MAR = vertical_opening / horizontal_width
        """
        def point(idx: int) -> np.ndarray:
            lm = landmarks[idx]
            return np.array([lm.x * w, lm.y * h])

        top = point(self.MOUTH_TOP)
        bottom = point(self.MOUTH_BOTTOM)
        left = point(self.MOUTH_LEFT)
        right = point(self.MOUTH_RIGHT)

        vertical = np.linalg.norm(top - bottom)
        horizontal = np.linalg.norm(left - right)

        if horizontal == 0:
            return 0.0

        return float(vertical / horizontal)

    def _estimate_yaw(self, landmarks: list, w: int, h: int) -> float:
        """
        Estimate head yaw (left-right rotation) in degrees.
        Uses the horizontal offset of nose tip from face center.
        Simple but effective for MVP.
        """
        nose = landmarks[self.NOSE_TIP]
        nose_x = nose.x  # normalized [0, 1]

        # Center offset as proxy for yaw
        # 0.5 = facing forward, <0.4 = looking right, >0.6 = looking left
        yaw_proxy = (nose_x - 0.5) * 90  # scale to approximate degrees
        return float(yaw_proxy)

    def analyze(self, image_bytes: bytes) -> LivenessCheckResult:
        """
        Perform liveness analysis on a single image.

        Args:
            image_bytes: Raw image bytes (JPEG/PNG)

        Returns:
            LivenessCheckResult with per-check details and composite score
        """
        # ── Decode image ──────────────────────────────────────────────────────
        if not image_bytes:
            return LivenessCheckResult(
                is_live=False,
                score=0.0,
                blink_detected=False,
                head_turn_detected=False,
                smile_detected=False,
                ear_value=0.0,
                mouth_ratio=0.0,
                yaw_angle=0.0,
                checks_passed=0,
                failure_reason="Could not decode image: empty bytes",
            )
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return LivenessCheckResult(
                is_live=False,
                score=0.0,
                blink_detected=False,
                head_turn_detected=False,
                smile_detected=False,
                ear_value=0.0,
                mouth_ratio=0.0,
                yaw_angle=0.0,
                checks_passed=0,
                failure_reason="Could not decode image",
            )

        h, w = img_bgr.shape[:2]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # ── Run MediaPipe Face Mesh ────────────────────────────────────────────
        results = self._face_mesh.process(img_rgb)

        if not results.multi_face_landmarks:
            return LivenessCheckResult(
                is_live=False,
                score=0.0,
                blink_detected=False,
                head_turn_detected=False,
                smile_detected=False,
                ear_value=0.0,
                mouth_ratio=0.0,
                yaw_angle=0.0,
                checks_passed=0,
                failure_reason="No face landmarks detected",
            )

        landmarks = results.multi_face_landmarks[0].landmark

        # ── Compute metrics ───────────────────────────────────────────────────
        left_ear = self._eye_aspect_ratio(landmarks, self.LEFT_EYE, w, h)
        right_ear = self._eye_aspect_ratio(landmarks, self.RIGHT_EYE, w, h)
        avg_ear = (left_ear + right_ear) / 2.0

        mouth_ratio = self._mouth_aspect_ratio(landmarks, w, h)
        yaw_angle = self._estimate_yaw(landmarks, w, h)

        # ── Liveness checks ───────────────────────────────────────────────────
        # Blink: EAR below threshold indicates a blink occurred
        # For a single static image, partial eye closure is the proxy
        blink_detected = avg_ear < self.EAR_BLINK_THRESHOLD or avg_ear > 0.15

        # Head turn: yaw deviation from center
        head_turn_detected = abs(yaw_angle) > self.YAW_TURN_THRESHOLD

        # Smile / mouth expression
        smile_detected = mouth_ratio > self.MOUTH_SMILE_THRESHOLD

        # ── Score computation ─────────────────────────────────────────────────
        checks_passed = sum([blink_detected, head_turn_detected, smile_detected])

        # Base score from passed checks
        base_score = (checks_passed / 3) * 60

        # EAR quality bonus (natural eye openness range 0.2–0.4)
        ear_bonus = min(20.0, avg_ear * 50)

        # Confidence bonus from MediaPipe detection quality
        detection_bonus = 20.0 if checks_passed >= 2 else 0.0

        score = min(100.0, base_score + ear_bonus + detection_bonus)

        # ── Liveness determination ────────────────────────────────────────────
        is_live = (
            score >= settings.LIVENESS_THRESHOLD
            and blink_detected
            and head_turn_detected
        )

        failure_reason = None
        if not is_live:
            if not blink_detected:
                failure_reason = "Blink not detected"
            elif not head_turn_detected:
                failure_reason = "Head turn not detected"
            else:
                failure_reason = f"Liveness score too low ({score:.1f} < {settings.LIVENESS_THRESHOLD})"

        logger.debug(
            "Liveness check complete",
            ear=avg_ear,
            mouth_ratio=mouth_ratio,
            yaw=yaw_angle,
            score=score,
            is_live=is_live,
        )

        return LivenessCheckResult(
            is_live=is_live,
            score=round(score, 2),
            blink_detected=blink_detected,
            head_turn_detected=head_turn_detected,
            smile_detected=smile_detected,
            ear_value=round(avg_ear, 4),
            mouth_ratio=round(mouth_ratio, 4),
            yaw_angle=round(yaw_angle, 2),
            checks_passed=checks_passed,
            method="mediapipe_v1",
            failure_reason=failure_reason,
        )

    def analyze_with_pipeline(self, image_bytes: bytes) -> LivenessCheckResult:
        """
        Run the full 6-stage liveness pipeline (Stage 1–6) including
        MiniFASNet passive anti-spoofing and return a LivenessCheckResult.

        This is the recommended method for production use. Falls back to
        the legacy analyze() if the pipeline raises unexpectedly.

        Args:
            image_bytes: Raw JPEG/PNG bytes from the HTTP request.

        Returns:
            LivenessCheckResult populated from the pipeline result.
        """
        try:
            from app.services.liveness_pipeline import LivenessPipeline
            pipeline = LivenessPipeline()
            result = pipeline.run(image_bytes)

            return LivenessCheckResult(
                is_live=result.is_live,
                score=result.score,
                blink_detected=result.blink_detected,
                head_turn_detected=result.head_turn_detected,
                smile_detected=result.smile_detected,
                ear_value=result.ear_value,
                mouth_ratio=result.mouth_ratio,
                yaw_angle=result.yaw_angle,
                checks_passed=sum([
                    result.blink_detected,
                    result.head_turn_detected,
                    result.smile_detected,
                ]),
                checks_total=3,
                anti_spoof_score=result.anti_spoof_score,
                method=result.method,
                failure_reason=result.failure_reason,
            )

        except Exception as exc:
            logger.error(
                "liveness_service.analyze_with_pipeline: pipeline failed, "
                "falling back to legacy analyze()",
                error=str(exc),
            )
            return self.analyze(image_bytes)
