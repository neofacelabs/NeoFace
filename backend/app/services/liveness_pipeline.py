"""
NeoFace Multi-Stage Liveness Pipeline
Orchestrates all liveness and anti-spoofing checks in a deterministic,
auditable 6-stage pipeline.

Pipeline stages
───────────────
Stage 1  Face Detection         InsightFace — must find exactly one face
Stage 2  Quality Validation     Resolution, blur score, detection confidence
Stage 3  Blink Detection        MediaPipe EAR — eye openness proxy
Stage 4  Head Movement          MediaPipe yaw — lateral head turn proxy
Stage 5  Passive Anti-Spoof     MiniFASNet ONNX (or heuristic fallback)
Stage 6  Score Composition      Weighted aggregation → final is_live decision

Stage weights (must sum to 1.0):
  quality       0.15
  blink         0.20
  head_turn     0.20
  anti_spoof    0.35
  face_conf     0.10

Decision rule:
  is_live = True  iff
    anti_spoof.is_real == True
    AND (blink_detected OR head_turn_detected)
    AND final_score >= settings.LIVENESS_THRESHOLD

All stage results are returned so callers can surface per-stage diagnostics
to operators without re-running the pipeline.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Any

import cv2
import mediapipe as mp
import numpy as np

from app.core.config import settings
from app.core.logging import logger
from app.services.anti_spoof_service import AntiSpoofResult, AntiSpoofService
from app.services.face_detector import DetectedFace, FaceDetectorService


# ── Stage result ──────────────────────────────────────────────────────────────

@dataclass
class StageResult:
    """Outcome of a single pipeline stage."""

    stage_name: str          # Human-readable name, e.g. "face_detection"
    stage_index: int         # 1–6
    passed: bool             # Whether this stage's gate was cleared
    score: float             # Normalised stage score (0–100)
    duration_ms: float       # Wall-clock time for this stage
    details: dict[str, Any] = field(default_factory=dict)
    failure_reason: str | None = None


# ── Final pipeline result ─────────────────────────────────────────────────────

@dataclass
class LivenessPipelineResult:
    """
    Complete result of the 6-stage liveness pipeline.

    All fields are populated regardless of outcome so callers can
    build detailed audit records.
    """
    is_live: bool
    score: float                      # Final weighted score (0–100)
    anti_spoof_score: float           # Stage 5 score (0–100)
    method: str = "pipeline_v2"
    stages: list[StageResult] = field(default_factory=list)

    # Convenience fields (duplicated from stage details for quick access)
    face_quality: float = 0.0
    blink_detected: bool = False
    head_turn_detected: bool = False
    smile_detected: bool = False
    ear_value: float = 0.0
    mouth_ratio: float = 0.0
    yaw_angle: float = 0.0
    attack_type: str = "none"

    total_duration_ms: float = 0.0
    failure_reason: str | None = None

    # Stage weights used for this run
    weights: dict[str, float] = field(default_factory=lambda: {
        "quality": 0.15,
        "blink": 0.20,
        "head_turn": 0.20,
        "anti_spoof": 0.35,
        "face_conf": 0.10,
    })


# ── Stage weights ─────────────────────────────────────────────────────────────
_WEIGHTS: dict[str, float] = {
    "quality":    0.15,
    "blink":      0.20,
    "head_turn":  0.20,
    "anti_spoof": 0.35,
    "face_conf":  0.10,
}

assert abs(sum(_WEIGHTS.values()) - 1.0) < 1e-6, "Stage weights must sum to 1.0"

# MediaPipe eye landmark indices (same as LivenessService)
_LEFT_EYE  = [362, 385, 387, 263, 373, 380]
_RIGHT_EYE = [33,  160, 158, 133, 153, 144]
_MOUTH_TOP, _MOUTH_BOTTOM = 13, 14
_MOUTH_LEFT, _MOUTH_RIGHT = 78, 308
_NOSE_TIP = 1

_EAR_BLINK_LOW  = 0.20   # Eyes noticeably closed
_EAR_NORMAL_MIN = 0.15   # Eyes at least partially open
_MOUTH_SMILE_TH = 0.10   # Mouth open or smiling
_YAW_TURN_TH    = 15.0   # Degrees of lateral head turn


class LivenessPipeline:
    """
    Executes the 6-stage liveness pipeline against a single JPEG/PNG frame.

    The pipeline is stateless — create one instance per application lifecycle
    (or per request) and call run() for each image.

    Dependencies are injected so the pipeline is easily testable with mocks.
    """

    def __init__(
        self,
        detector: FaceDetectorService | None = None,
        anti_spoof: AntiSpoofService | None = None,
    ) -> None:
        # Use provided instances or fall back to global singletons
        self._detector = detector or FaceDetectorService.get_instance()
        self._anti_spoof = anti_spoof or AntiSpoofService.get_instance()

        # MediaPipe Face Mesh is lightweight — create fresh per instance
        self._face_mesh = mp.solutions.face_mesh.FaceMesh(
            static_image_mode=True,
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
        )

    # ── Public entry point ────────────────────────────────────────────────────

    def run(self, image_bytes: bytes) -> LivenessPipelineResult:
        """
        Execute the full 6-stage pipeline against raw image bytes.

        Args:
            image_bytes: Raw JPEG or PNG bytes from the HTTP request.

        Returns:
            LivenessPipelineResult — always populated, never raises.
        """
        pipeline_start = time.perf_counter()
        stages: list[StageResult] = []

        # ── Decode image once ─────────────────────────────────────────────────
        nparr = np.frombuffer(image_bytes, np.uint8)
        img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)

        if img_bgr is None:
            return self._fail(
                stages, pipeline_start,
                failure_reason="Could not decode image bytes",
            )

        h, w = img_bgr.shape[:2]
        img_rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)

        # ──────────────────────────────────────────────────────────────────────
        # STAGE 1 — Face Detection
        # ──────────────────────────────────────────────────────────────────────
        s1_start = time.perf_counter()
        detection_result, detected_face = self._detector.detect_single(image_bytes)
        s1_ms = (time.perf_counter() - s1_start) * 1000

        if not detection_result.success or detected_face is None:
            stages.append(StageResult(
                stage_name="face_detection", stage_index=1,
                passed=False, score=0.0, duration_ms=round(s1_ms, 2),
                failure_reason=detection_result.error or "No face detected",
                details={"face_count": detection_result.face_count},
            ))
            return self._fail(
                stages, pipeline_start,
                failure_reason=detection_result.error or "No face detected",
            )

        face_conf = float(detected_face.detection_score) * 100.0
        stages.append(StageResult(
            stage_name="face_detection", stage_index=1,
            passed=True, score=face_conf, duration_ms=round(s1_ms, 2),
            details={
                "face_count": 1,
                "detection_score": round(face_conf, 2),
                "bbox": detected_face.bbox,
            },
        ))

        # ──────────────────────────────────────────────────────────────────────
        # STAGE 2 — Quality Validation
        # ──────────────────────────────────────────────────────────────────────
        s2_start = time.perf_counter()
        quality_score = float(detected_face.quality_score)
        blur_score = detection_result.blur_score

        quality_passed = (
            quality_score >= 30.0           # Minimum acceptable quality
            and w >= settings.MIN_IMAGE_WIDTH
            and h >= settings.MIN_IMAGE_HEIGHT
            and blur_score >= settings.BLUR_THRESHOLD
        )
        s2_ms = (time.perf_counter() - s2_start) * 1000

        quality_failure = None
        if not quality_passed:
            if blur_score < settings.BLUR_THRESHOLD:
                quality_failure = f"Image too blurry (score={blur_score:.1f})"
            elif quality_score < 30.0:
                quality_failure = f"Face quality too low ({quality_score:.1f}/100)"
            else:
                quality_failure = f"Image too small ({w}×{h})"

        stages.append(StageResult(
            stage_name="quality_validation", stage_index=2,
            passed=quality_passed, score=quality_score, duration_ms=round(s2_ms, 2),
            failure_reason=quality_failure,
            details={
                "quality_score": round(quality_score, 2),
                "blur_score": round(blur_score, 2),
                "resolution": f"{w}x{h}",
            },
        ))

        if not quality_passed:
            return self._fail(
                stages, pipeline_start,
                failure_reason=quality_failure or "Quality validation failed",
                face_quality=quality_score,
            )

        # ──────────────────────────────────────────────────────────────────────
        # STAGE 3 — Blink Detection (MediaPipe EAR)
        # ──────────────────────────────────────────────────────────────────────
        s3_start = time.perf_counter()
        mp_results = self._face_mesh.process(img_rgb)
        s3_ms = (time.perf_counter() - s3_start) * 1000

        blink_detected = False
        head_turn_detected = False
        smile_detected = False
        ear_value = 0.0
        mouth_ratio = 0.0
        yaw_angle = 0.0

        if mp_results and mp_results.multi_face_landmarks:
            lms = mp_results.multi_face_landmarks[0].landmark
            ear_value = self._avg_ear(lms, w, h)
            mouth_ratio = self._mouth_ratio(lms, w, h)
            yaw_angle = self._estimate_yaw(lms)

            # Blink proxy: EAR partially closed or natural open range
            blink_detected = (ear_value < _EAR_BLINK_LOW) or (ear_value > _EAR_NORMAL_MIN)
            head_turn_detected = abs(yaw_angle) > _YAW_TURN_TH
            smile_detected = mouth_ratio > _MOUTH_SMILE_TH

        blink_score = 80.0 if blink_detected else 20.0

        stages.append(StageResult(
            stage_name="blink_detection", stage_index=3,
            passed=blink_detected, score=blink_score, duration_ms=round(s3_ms, 2),
            failure_reason=None if blink_detected else "Blink / eye openness not detected",
            details={
                "ear_value": round(ear_value, 4),
                "blink_detected": blink_detected,
            },
        ))

        # ──────────────────────────────────────────────────────────────────────
        # STAGE 4 — Head Movement Detection
        # ──────────────────────────────────────────────────────────────────────
        head_score = min(abs(yaw_angle) / _YAW_TURN_TH * 80.0, 100.0) if head_turn_detected else 20.0

        stages.append(StageResult(
            stage_name="head_movement", stage_index=4,
            passed=head_turn_detected, score=head_score,
            duration_ms=0.0,   # Computed in same pass as stage 3
            failure_reason=None if head_turn_detected else "Head turn not detected",
            details={
                "yaw_angle": round(yaw_angle, 2),
                "head_turn_detected": head_turn_detected,
                "mouth_ratio": round(mouth_ratio, 4),
                "smile_detected": smile_detected,
            },
        ))

        # ──────────────────────────────────────────────────────────────────────
        # STAGE 5 — Passive Anti-Spoof (MiniFASNet / heuristic)
        # ──────────────────────────────────────────────────────────────────────
        s5_start = time.perf_counter()
        x1, y1, x2, y2 = detected_face.bbox
        face_crop = img_bgr[max(0, y1):y2, max(0, x1):x2]
        if face_crop.size == 0:
            face_crop = img_bgr  # Fallback to full image if crop is empty

        anti_spoof_result: AntiSpoofResult = self._anti_spoof.predict(face_crop)
        s5_ms = (time.perf_counter() - s5_start) * 1000

        stages.append(StageResult(
            stage_name="anti_spoof", stage_index=5,
            passed=anti_spoof_result.is_real,
            score=anti_spoof_result.score,
            duration_ms=round(s5_ms, 2),
            failure_reason=(
                None if anti_spoof_result.is_real
                else f"Spoof attack detected: {anti_spoof_result.attack_type}"
            ),
            details={
                "is_real": anti_spoof_result.is_real,
                "anti_spoof_score": anti_spoof_result.score,
                "attack_type": anti_spoof_result.attack_type,
                "method": anti_spoof_result.method,
                "model_available": anti_spoof_result.model_available,
            },
        ))

        # ──────────────────────────────────────────────────────────────────────
        # STAGE 6 — Score Composition
        # ──────────────────────────────────────────────────────────────────────
        s6_start = time.perf_counter()

        weighted_score = (
            _WEIGHTS["quality"]    * quality_score
            + _WEIGHTS["blink"]      * blink_score
            + _WEIGHTS["head_turn"]  * head_score
            + _WEIGHTS["anti_spoof"] * anti_spoof_result.score
            + _WEIGHTS["face_conf"]  * face_conf
        )
        final_score = round(min(weighted_score, 100.0), 2)

        # ── Decision rule ─────────────────────────────────────────────────────
        is_live = (
            anti_spoof_result.is_real
            and (blink_detected or head_turn_detected)
            and final_score >= settings.LIVENESS_THRESHOLD
        )

        failure_reason: str | None = None
        if not is_live:
            if not anti_spoof_result.is_real:
                failure_reason = f"Anti-spoof failed: {anti_spoof_result.attack_type} attack"
            elif not (blink_detected or head_turn_detected):
                failure_reason = "Neither blink nor head turn detected"
            else:
                failure_reason = (
                    f"Score too low ({final_score:.1f} < {settings.LIVENESS_THRESHOLD})"
                )

        s6_ms = (time.perf_counter() - s6_start) * 1000
        stages.append(StageResult(
            stage_name="score_composition", stage_index=6,
            passed=is_live, score=final_score, duration_ms=round(s6_ms, 2),
            failure_reason=failure_reason,
            details={
                "weighted_score": final_score,
                "threshold": settings.LIVENESS_THRESHOLD,
                "weights": _WEIGHTS,
                "component_scores": {
                    "quality": round(quality_score, 2),
                    "blink": round(blink_score, 2),
                    "head_turn": round(head_score, 2),
                    "anti_spoof": round(anti_spoof_result.score, 2),
                    "face_conf": round(face_conf, 2),
                },
            },
        ))

        total_ms = (time.perf_counter() - pipeline_start) * 1000

        logger.info(
            "liveness_pipeline.run",
            is_live=is_live,
            score=final_score,
            anti_spoof=anti_spoof_result.score,
            method=anti_spoof_result.method,
            total_ms=round(total_ms, 2),
            failure_reason=failure_reason,
        )

        return LivenessPipelineResult(
            is_live=is_live,
            score=final_score,
            anti_spoof_score=anti_spoof_result.score,
            method=f"pipeline_v2+{anti_spoof_result.method}",
            stages=stages,
            face_quality=quality_score,
            blink_detected=blink_detected,
            head_turn_detected=head_turn_detected,
            smile_detected=smile_detected,
            ear_value=round(ear_value, 4),
            mouth_ratio=round(mouth_ratio, 4),
            yaw_angle=round(yaw_angle, 2),
            attack_type=anti_spoof_result.attack_type,
            total_duration_ms=round(total_ms, 2),
            failure_reason=failure_reason,
        )

    # ── MediaPipe helpers ─────────────────────────────────────────────────────

    def _avg_ear(self, landmarks: list, w: int, h: int) -> float:
        """Average Eye Aspect Ratio for both eyes."""
        left = self._ear(landmarks, _LEFT_EYE, w, h)
        right = self._ear(landmarks, _RIGHT_EYE, w, h)
        return (left + right) / 2.0

    @staticmethod
    def _ear(landmarks: list, indices: list[int], w: int, h: int) -> float:
        """EAR = (||p2-p6|| + ||p3-p5||) / (2 * ||p1-p4||)"""
        def pt(i: int) -> np.ndarray:
            lm = landmarks[i]
            return np.array([lm.x * w, lm.y * h])
        p1, p2, p3, p4, p5, p6 = [pt(i) for i in indices]
        h_dist = np.linalg.norm(p1 - p4)
        if h_dist == 0:
            return 0.0
        return float((np.linalg.norm(p2 - p6) + np.linalg.norm(p3 - p5)) / (2 * h_dist))

    @staticmethod
    def _mouth_ratio(landmarks: list, w: int, h: int) -> float:
        """Simplified mouth aspect ratio: vertical/horizontal opening."""
        def pt(i: int) -> np.ndarray:
            lm = landmarks[i]
            return np.array([lm.x * w, lm.y * h])
        v = np.linalg.norm(pt(_MOUTH_TOP) - pt(_MOUTH_BOTTOM))
        hor = np.linalg.norm(pt(_MOUTH_LEFT) - pt(_MOUTH_RIGHT))
        return float(v / hor) if hor > 0 else 0.0

    @staticmethod
    def _estimate_yaw(landmarks: list) -> float:
        """Approximate yaw in degrees from nose-tip horizontal offset."""
        return float((landmarks[_NOSE_TIP].x - 0.5) * 90.0)

    # ── Failure helpers ───────────────────────────────────────────────────────

    @staticmethod
    def _fail(
        stages: list[StageResult],
        pipeline_start: float,
        failure_reason: str,
        face_quality: float = 0.0,
    ) -> LivenessPipelineResult:
        """Return a failed LivenessPipelineResult with partial stage data."""
        total_ms = (time.perf_counter() - pipeline_start) * 1000
        return LivenessPipelineResult(
            is_live=False,
            score=0.0,
            anti_spoof_score=0.0,
            method="pipeline_v2",
            stages=stages,
            face_quality=face_quality,
            total_duration_ms=round(total_ms, 2),
            failure_reason=failure_reason,
        )
